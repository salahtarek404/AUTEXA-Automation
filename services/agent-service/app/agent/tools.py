import json
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.rag.retriever import retrieve_chunks

def qualify_lead(db: Session, lead_id: int, intent: str, priority: str) -> str:
    """
    Qualifies a lead by setting their intent (buying, browsing, support) and priority (hot, warm, cold).
    Also updates lead status to 'qualified'. Run this automatically after a few messages or when intent is clear.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})
    
    lead.intent = intent.lower()
    lead.priority = priority.lower()
    lead.status = "qualified"
    db.commit()
    db.refresh(lead)
    
    return json.dumps({
        "status": "success",
        "message": f"Lead {lead_id} qualified as {intent} (priority: {priority}).",
        "lead": {
            "id": lead.id,
            "intent": lead.intent,
            "priority": lead.priority,
            "status": lead.status
        }
    })

def create_lead(db: Session, phone: str, source: str, name: str = "Guest", email: str = None, business_type: str = None, service_requested: str = None) -> str:
    """
    Creates a new lead in the database with contact info and details from the conversation.
    """
    lead = Lead(
        name=name,
        phone=phone,
        email=email,
        source=source,
        business_type=business_type,
        service_requested=service_requested,
        status="new"
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    return json.dumps({
        "status": "success",
        "message": f"Lead created successfully with ID {lead.id}.",
        "lead_id": lead.id
    })

def update_lead(db: Session, lead_id: int, name: str = None, email: str = None, phone: str = None, business_type: str = None, service_requested: str = None) -> str:
    """
    Updates an existing lead's fields as new information is gathered during the conversation.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return json.dumps({"status": "error", "message": f"Lead with ID {lead_id} not found."})
    
    if name: lead.name = name
    if email: lead.email = email
    if phone: lead.phone = phone
    if business_type: lead.business_type = business_type
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
            "service_requested": lead.service_requested
        }
    })

def search_services(db: Session, query: str) -> str:
    """
    Queries the knowledge base for details about Autexa's services, packages, pricing, subscription options, and FAQs.
    """
    chunks = retrieve_chunks(db, query, limit=3)
    # Exclude case studies to keep search relevant to service details
    filtered_chunks = [c for c in chunks if c.source_doc != "case_studies.md"]
    if not filtered_chunks:
        filtered_chunks = retrieve_chunks(db, query, limit=2, filter_source="services.md")
        
    results = []
    for chunk in filtered_chunks:
        results.append(f"Source: {chunk.source_doc}\nContent:\n{chunk.content}\n---")
        
    return "\n\n".join(results) if results else "No relevant service details found."

def search_case_studies(db: Session, query: str) -> str:
    """
    Queries the knowledge base for specific client case studies, success stories, and metrics.
    """
    chunks = retrieve_chunks(db, query, limit=2, filter_source="case_studies.md")
    results = []
    for chunk in chunks:
        results.append(f"Source: {chunk.source_doc}\nContent:\n{chunk.content}\n---")
        
    return "\n\n".join(results) if results else "No relevant case studies found."
