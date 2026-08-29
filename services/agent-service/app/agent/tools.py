import json
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.followup import Followup
from app.models.proposal import Proposal
from app.rag.retriever import retrieve_chunks

# ---------------------------------------------------------------------------
# Phase 2 Tools (unchanged)
# ---------------------------------------------------------------------------

def qualify_lead(db: Session, lead_id: int, intent: str, priority: str) -> str:
    """
    Qualifies a lead by setting intent and priority. Automatically triggers
    notify_sales_team if priority == 'hot'.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})

    lead.intent = intent.lower()
    lead.priority = priority.lower()
    lead.status = "qualified"
    db.commit()
    db.refresh(lead)

    result_payload = {
        "status": "success",
        "message": f"Lead {lead_id} qualified as {intent} (priority: {priority}).",
        "lead": {
            "id": lead.id,
            "intent": lead.intent,
            "priority": lead.priority,
            "status": lead.status,
        },
    }

    # Auto-trigger hot-lead notification — enforced in the tool, not just LLM
    if lead.priority == "hot":
        notify_result = notify_sales_team(db, lead_id)
        result_payload["notification_triggered"] = notify_result

    return json.dumps(result_payload)


def create_lead(
    db: Session,
    phone: str,
    source: str,
    name: str = "Guest",
    email: str = None,
    business_type: str = None,
    service_requested: str = None,
) -> str:
    lead = Lead(
        name=name,
        phone=phone,
        email=email,
        source=source,
        business_type=business_type,
        service_requested=service_requested,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return json.dumps({
        "status": "success",
        "message": f"Lead created successfully with ID {lead.id}.",
        "lead_id": lead.id,
    })


def update_lead(
    db: Session,
    lead_id: int,
    name: str = None,
    email: str = None,
    phone: str = None,
    business_type: str = None,
    service_requested: str = None,
) -> str:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})

    if name:             lead.name = name
    if email:            lead.email = email
    if phone:            lead.phone = phone
    if business_type:    lead.business_type = business_type
    if service_requested: lead.service_requested = service_requested

    db.commit()
    db.refresh(lead)

    return json.dumps({
        "status": "success",
        "message": f"Lead {lead_id} updated successfully.",
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "business_type": lead.business_type,
            "service_requested": lead.service_requested,
        },
    })


def search_services(db: Session, query: str) -> str:
    chunks = retrieve_chunks(db, query, limit=3)
    filtered_chunks = [c for c in chunks if c.source_doc != "case_studies.md"]
    if not filtered_chunks:
        filtered_chunks = retrieve_chunks(db, query, limit=2, filter_source="services.md")

    results = []
    for chunk in filtered_chunks:
        results.append(f"Source: {chunk.source_doc}\nContent:\n{chunk.content}\n---")

    return "\n\n".join(results) if results else "No relevant service details found."


def search_case_studies(db: Session, query: str) -> str:
    chunks = retrieve_chunks(db, query, limit=2, filter_source="case_studies.md")
    results = []
    for chunk in chunks:
        results.append(f"Source: {chunk.source_doc}\nContent:\n{chunk.content}\n---")

    return "\n\n".join(results) if results else "No relevant case studies found."


# ---------------------------------------------------------------------------
# Phase 3 Tools (new)
# ---------------------------------------------------------------------------

def schedule_followup(
    db: Session,
    lead_id: int,
    hours_from_now: float = 48.0,
    message_type: str = "auto_message",
) -> str:
    """
    Schedules an automated follow-up message for a lead.
    The Celery worker will pick this up and send via the lead's original channel.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})

    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    channel = lead.source if lead.source in ("whatsapp",) else "website"

    followup = Followup(
        lead_id=lead_id,
        scheduled_at=scheduled_at,
        type=message_type,
        channel=channel,
        status="pending",
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)

    return json.dumps({
        "status": "success",
        "message": f"Follow-up scheduled for lead {lead_id} in {hours_from_now}h.",
        "followup": {
            "id": followup.id,
            "scheduled_at": scheduled_at.isoformat(),
            "type": message_type,
            "channel": channel,
        },
    })


def notify_sales_team(db: Session, lead_id: int) -> str:
    """
    Fires a webhook to n8n which forwards a hot-lead alert to Slack/email.
    Called automatically by qualify_lead when priority=hot, and available
    as a standalone LLM-callable tool.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})

    n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
    if not n8n_url:
        return json.dumps({
            "status": "skipped",
            "message": "N8N_WEBHOOK_URL not configured — notification skipped.",
        })

    payload = {
        "lead_id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "business_type": lead.business_type,
        "service_requested": lead.service_requested,
        "intent": lead.intent,
        "priority": lead.priority,
        "source": lead.source,
    }

    try:
        response = httpx.post(n8n_url, json=payload, timeout=10.0)
        response.raise_for_status()
        return json.dumps({
            "status": "success",
            "message": f"Sales team notified about hot lead {lead_id} via n8n.",
            "n8n_status": response.status_code,
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to notify sales team: {e}",
        })


# Pricing tiers pulled from pricing.md — framed as estimates, never guarantees
PRICING_TIERS = {
    "starter": {
        "scope": "Single-channel AI automation (website widget). Includes basic RAG knowledge base, up to 1,000 messages/month.",
        "price": "$150 – $300/month (rough estimate)",
        "timeline": "1–2 weeks to deploy",
    },
    "growth": {
        "scope": "Multi-channel automation (up to 3 channels). Advanced RAG, auto-updating knowledge base, up to 5,000 messages/month, custom lead qualification.",
        "price": "$400 – $800/month (rough estimate)",
        "timeline": "2–4 weeks to deploy",
    },
    "enterprise": {
        "scope": "Unlimited channels, custom CRM sync (Salesforce/HubSpot), dedicated LLM deployment, custom analytics dashboard, priority SLA.",
        "price": "Starting from $1,200/month (scoped individually)",
        "timeline": "4–8 weeks, scoped per project",
    },
}


def generate_proposal(db: Session, lead_id: int) -> str:
    """
    Drafts a proposal for a qualified lead. Creates a DB row with status='draft'.
    NEVER sends automatically — a human must approve it in the dashboard first.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})

    if lead.status not in ("qualified", "proposal_sent"):
        return json.dumps({
            "status": "error",
            "message": f"Lead {lead_id} is not yet qualified (status: {lead.status}). Qualify the lead first.",
        })

    # Pick the pricing tier that best matches the service requested
    service_lower = (lead.service_requested or "").lower()
    if "enterprise" in service_lower or "unlimited" in service_lower or "custom" in service_lower:
        tier = PRICING_TIERS["enterprise"]
    elif "growth" in service_lower or "multi" in service_lower or "whatsapp" in service_lower:
        tier = PRICING_TIERS["growth"]
    else:
        tier = PRICING_TIERS["starter"]

    service_scope = (
        f"Proposed solution for {lead.business_type or 'your business'}: {tier['scope']}"
    )

    proposal = Proposal(
        lead_id=lead_id,
        service_scope=service_scope,
        estimated_price=tier["price"],
        estimated_timeline=tier["timeline"],
        status="draft",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return json.dumps({
        "status": "success",
        "message": (
            f"Proposal draft created for lead {lead_id}. "
            "This is a draft estimate — pending human approval before sending."
        ),
        "proposal": {
            "id": proposal.id,
            "service_scope": proposal.service_scope,
            "estimated_price": proposal.estimated_price,
            "estimated_timeline": proposal.estimated_timeline,
            "status": "draft",
            "disclaimer": "All prices are rough estimates only. Final pricing requires a scoping call.",
        },
    })
