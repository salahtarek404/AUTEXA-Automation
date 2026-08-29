from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings

from app.db.session import engine, get_db, Base
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.proposal import Proposal
from app.models import Followup  # ensures table creation
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.orchestrator import orchestrator

# For MVP Phase 1, create tables automatically on startup
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    except Exception as e:
        print(f"Could not create vector extension: {e}")
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Autexa Agent Service"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Receives message, fetches LLM reply, and saves to DB."""
    lead = db.query(Lead).filter(Lead.phone == request.sender_id).first()
    if not lead:
        lead = Lead(name="Guest", phone=request.sender_id, source=request.channel)
        db.add(lead)
        db.commit()
        db.refresh(lead)

    conversation = db.query(Conversation).filter(Conversation.lead_id == lead.id).first()
    if not conversation:
        conversation = Conversation(lead_id=lead.id, channel=request.channel, messages=[])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_msg = {"role": "user", "content": request.message}
    updated_messages = list(conversation.messages) + [user_msg]
    conversation.messages = updated_messages

    bot_reply = orchestrator.generate_reply(db, lead, conversation.messages)

    bot_msg = {"role": "assistant", "content": bot_reply}
    updated_messages = list(conversation.messages) + [bot_msg]
    conversation.messages = updated_messages
    db.commit()

    return ChatResponse(reply=bot_reply)


@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    """Expose leads API for the frontend dashboard."""
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return leads


# ---------------------------------------------------------------------------
# Phase 3: Proposals endpoints
# ---------------------------------------------------------------------------

@app.get("/api/proposals")
def get_proposals(db: Session = Depends(get_db)):
    """Returns all proposals with joined lead info for the dashboard."""
    rows = (
        db.query(Proposal, Lead)
        .join(Lead, Proposal.lead_id == Lead.id)
        .order_by(Proposal.created_at.desc())
        .all()
    )
    result = []
    for proposal, lead in rows:
        result.append({
            "id": proposal.id,
            "lead_id": proposal.lead_id,
            "lead_name": lead.name,
            "lead_email": lead.email,
            "lead_phone": lead.phone,
            "service_scope": proposal.service_scope,
            "estimated_price": proposal.estimated_price,
            "estimated_timeline": proposal.estimated_timeline,
            "status": proposal.status,
            "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
        })
    return result


@app.patch("/api/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """
    Marks a draft proposal as approved. Does NOT send anything to the customer.
    Human is responsible for manually dispatching it after approval.
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")
    if proposal.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal {proposal_id} is already '{proposal.status}' — only draft proposals can be approved."
        )

    proposal.status = "approved"
    db.commit()
    db.refresh(proposal)

    return {
        "id": proposal.id,
        "status": proposal.status,
        "message": "Proposal approved. No message has been sent to the customer — dispatch it manually.",
    }
