from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings

from app.db.session import engine, get_db, Base
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.orchestrator import orchestrator

# For MVP Phase 1, create tables automatically
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
    # Create or update a dummy lead for Phase 1
    lead = db.query(Lead).filter(Lead.phone == request.sender_id).first()
    if not lead:
        lead = Lead(name="Guest", phone=request.sender_id, source=request.channel)
        db.add(lead)
        db.commit()
        db.refresh(lead)

    # Find conversation or create new
    conversation = db.query(Conversation).filter(Conversation.lead_id == lead.id).first()
    if not conversation:
        conversation = Conversation(lead_id=lead.id, channel=request.channel, messages=[])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Append user message
    user_msg = {"role": "user", "content": request.message}
    
    # We must explicitly create a new list for JSONB to register the mutation in SQLAlchemy easily
    updated_messages = list(conversation.messages) + [user_msg]
    conversation.messages = updated_messages

    # Generate reply
    bot_reply = orchestrator.generate_reply(db, lead, conversation.messages)
    
    # Append bot reply
    bot_msg = {"role": "assistant", "content": bot_reply}
    updated_messages = list(conversation.messages) + [bot_msg]
    conversation.messages = updated_messages
    db.commit()

    return ChatResponse(reply=bot_reply)

@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    """Expose leads API for the frontend dashboard"""
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return leads
