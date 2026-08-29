from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from datetime import datetime, timezone, date
from sqlalchemy import func


from app.db.session import engine, get_db, Base, SessionLocal
from app.models.tenant import TenantConfig
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.proposal import Proposal
from app.models import Followup  # ensures table creation
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.orchestrator import orchestrator

# For MVP Phase 1, create tables automatically on startup
from sqlalchemy import text
import os
with engine.connect() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    except Exception as e:
        print(f"Could not create vector extension: {e}")
Base.metadata.create_all(bind=engine)

# Seed tenants on startup
with SessionLocal() as db:
    if not db.query(TenantConfig).filter(TenantConfig.tenant_id == "autexa").first():
        autexa_tenant = TenantConfig(
            tenant_id="autexa",
            name="Autexa (Tenant Zero)",
            whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", "autexa_verify_token"),
            whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            instagram_verify_token=os.getenv("INSTAGRAM_VERIFY_TOKEN", "autexa_instagram_verify_token"),
            instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        )
        db.add(autexa_tenant)
        
        db.add(TenantConfig(
            tenant_id="restaurant",
            name="Restaurant Sandbox",
            whatsapp_verify_token="restaurant_verify_token",
            whatsapp_access_token="mock_restaurant_access_token",
            whatsapp_phone_number_id="mock_restaurant_phone_number_id",
            instagram_verify_token="restaurant_instagram_verify_token",
            instagram_access_token="mock_restaurant_instagram_access_token"
        ))
        db.add(TenantConfig(
            tenant_id="real_estate",
            name="Real Estate Sandbox",
            whatsapp_verify_token="real_estate_verify_token",
            whatsapp_access_token="mock_real_estate_access_token",
            whatsapp_phone_number_id="mock_real_estate_phone_number_id",
            instagram_verify_token="real_estate_instagram_verify_token",
            instagram_access_token="mock_real_estate_instagram_access_token"
        ))
        db.add(TenantConfig(
            tenant_id="ecommerce",
            name="E-commerce Sandbox",
            whatsapp_verify_token="ecommerce_verify_token",
            whatsapp_access_token="mock_ecommerce_access_token",
            whatsapp_phone_number_id="mock_ecommerce_phone_number_id",
            instagram_verify_token="ecommerce_instagram_verify_token",
            instagram_access_token="mock_ecommerce_instagram_access_token"
        ))
        db.commit()
        print("[Startup] Seeded tenant sandbox profiles successfully.")

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


def get_tenant_id(
    x_tenant_id: str = Header(None, alias="X-Tenant-ID"),
    tenant_id: str = Query(None)
) -> str:
    if x_tenant_id:
        return x_tenant_id
    if tenant_id:
        return tenant_id
    return "autexa"


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Receives message, fetches LLM reply, and saves to DB."""
    # Determine the tenant from request body or fallback
    tenant_id = request.tenant_id or "autexa"

    # Channel-aware lead query (scoped by tenant)
    lead = None
    if request.channel == "whatsapp":
        lead = db.query(Lead).filter(Lead.phone == request.sender_id, Lead.tenant_id == tenant_id).first()
    elif request.channel == "instagram":
        lead = db.query(Lead).filter(Lead.instagram_handle == request.sender_id, Lead.tenant_id == tenant_id).first()
    else:
        lead = db.query(Lead).filter(Lead.phone == request.sender_id, Lead.tenant_id == tenant_id).first()

    if not lead:
        if request.channel == "whatsapp":
            lead = Lead(name="Guest", phone=request.sender_id, source=request.channel, tenant_id=tenant_id)
        elif request.channel == "instagram":
            lead = Lead(name="Guest", instagram_handle=request.sender_id, source=request.channel, tenant_id=tenant_id)
        else:
            lead = Lead(name="Guest", phone=request.sender_id, source=request.channel, tenant_id=tenant_id)
        db.add(lead)
        db.commit()
        db.refresh(lead)

    # Scoped conversation by lead_id AND channel AND tenant_id
    conversation = db.query(Conversation).filter(
        Conversation.lead_id == lead.id, 
        Conversation.channel == request.channel,
        Conversation.tenant_id == tenant_id
    ).first()

    if not conversation:
        conversation = Conversation(lead_id=lead.id, channel=request.channel, messages=[], tenant_id=tenant_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    timestamp_str = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": request.message, "timestamp": timestamp_str}
    updated_messages = list(conversation.messages) + [user_msg]
    conversation.messages = updated_messages

    bot_reply = orchestrator.generate_reply(db, lead, conversation.messages)

    bot_msg = {"role": "assistant", "content": bot_reply, "timestamp": datetime.now(timezone.utc).isoformat()}
    updated_messages = list(conversation.messages) + [bot_msg]
    conversation.messages = updated_messages
    db.commit()

    return ChatResponse(reply=bot_reply)


@app.get("/api/leads")
def get_leads(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    """Expose leads API for the frontend dashboard."""
    leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).order_by(Lead.created_at.desc()).all()
    return leads


@app.get("/api/analytics")
def get_analytics(
    start_date: str = Query(None),
    end_date: str = Query(None),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """Computes conversion rates, response times, and source performance."""
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD.")
    if end_date:
        try:
            # Include the entire day of the end_date
            end_dt = datetime.strptime(f"{end_date} 23:59:59.999999", "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD.")

    # 1. Total and won leads query with date and tenant filters
    leads_query = db.query(Lead).filter(Lead.tenant_id == tenant_id)
    if start_dt:
        leads_query = leads_query.filter(Lead.created_at >= start_dt)
    if end_dt:
        leads_query = leads_query.filter(Lead.created_at <= end_dt)
    
    leads = leads_query.all()
    total_leads = len(leads)
    won_leads = sum(1 for l in leads if l.status == "won")
    
    conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0.0

    # 2. Average Response Time
    # Get all conversations for these leads scoped by tenant
    lead_ids = [l.id for l in leads]
    conversations = []
    if lead_ids:
        conversations = db.query(Conversation).filter(
            Conversation.lead_id.in_(lead_ids),
            Conversation.tenant_id == tenant_id
        ).all()
    
    response_times = []
    for conv in conversations:
        messages = conv.messages or []
        first_user_time = None
        first_agent_time = None
        
        for msg in messages:
            role = msg.get("role")
            ts_str = msg.get("timestamp")
            
            if not ts_str:
                continue
                
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                continue
                
            if role == "user" and first_user_time is None:
                first_user_time = ts
            elif role == "assistant" and first_user_time is not None and first_agent_time is None:
                first_agent_time = ts
                break # We found the first reply
                
        if first_user_time and first_agent_time:
            diff_seconds = (first_agent_time - first_user_time).total_seconds()
            if diff_seconds >= 0: # Ensure no negative times
                response_times.append(diff_seconds)

    avg_response_time = (sum(response_times) / len(response_times)) if response_times else None

    # 3. Lead Source Performance
    source_stats = {}
    for l in leads:
        src = l.source or "unknown"
        if src not in source_stats:
            source_stats[src] = {"total": 0, "won": 0}
        source_stats[src]["total"] += 1
        if l.status == "won":
            source_stats[src]["won"] += 1
            
    source_performance = []
    for src, stats in source_stats.items():
        total = stats["total"]
        won = stats["won"]
        rate = (won / total * 100) if total > 0 else 0.0
        source_performance.append({
            "source": src,
            "total_leads": total,
            "converted_leads": won,
            "conversion_rate": round(rate, 2)
        })

    return {
        "conversion_rate": round(conversion_rate, 2),
        "average_response_time_seconds": round(avg_response_time, 2) if avg_response_time is not None else None,
        "source_performance": source_performance,
        "total_leads": total_leads,
        "converted_leads": won_leads
    }



# ---------------------------------------------------------------------------
# Phase 3: Proposals endpoints
# ---------------------------------------------------------------------------

@app.get("/api/proposals")
def get_proposals(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    """Returns all proposals with joined lead info for the dashboard."""
    rows = (
        db.query(Proposal, Lead)
        .join(Lead, Proposal.lead_id == Lead.id)
        .filter(Proposal.tenant_id == tenant_id)
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
def approve_proposal(proposal_id: int, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    """
    Marks a draft proposal as approved. Does NOT send anything to the customer.
    Human is responsible for manually dispatching it after approval.
    """
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.tenant_id == tenant_id).first()
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


@app.get("/api/tenants/{tenant_id}/config")
def get_tenant_config(tenant_id: str, db: Session = Depends(get_db)):
    """Internal endpoint for channels-service to fetch tenant-specific tokens/credentials dynamically."""
    config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found.")
    return {
        "tenant_id": config.tenant_id,
        "name": config.name,
        "whatsapp_verify_token": config.whatsapp_verify_token,
        "whatsapp_access_token": config.whatsapp_access_token,
        "whatsapp_phone_number_id": config.whatsapp_phone_number_id,
        "instagram_verify_token": config.instagram_verify_token,
        "instagram_access_token": config.instagram_access_token
    }

