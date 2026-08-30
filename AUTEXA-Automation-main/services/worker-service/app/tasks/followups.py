"""
Celery periodic task: process due follow-ups.

Every 60 seconds, finds followup rows where:
  - status = 'pending'
  - scheduled_at <= now (UTC)

For each: sends a follow-up message back through the lead's original channel,
marks the row 'sent', and writes a ToolCallLog entry for the audit trail.
"""

import os
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.celery_app import celery_app

# ---------------------------------------------------------------------------
# Minimal DB setup — worker-service has its own engine, same DB as agent-service
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
CHANNELS_SERVICE_URL = os.getenv("CHANNELS_SERVICE_URL", "http://channels-service:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@celery_app.task
def process_due_followups():
    """Scan for pending, past-due follow-ups and dispatch them."""
    db = SessionLocal()
    now_utc = datetime.now(timezone.utc)

    try:
        # Raw SQL — avoids duplicating SQLAlchemy models in the worker service
        due_rows = db.execute(
            text("""
                SELECT f.id, f.lead_id, f.channel, f.type,
                       l.name, l.service_requested, l.phone
                FROM followups f
                JOIN leads l ON l.id = f.lead_id
                WHERE f.status = 'pending'
                  AND f.scheduled_at <= :now
            """),
            {"now": now_utc}
        ).fetchall()

        print(f"[Worker] Found {len(due_rows)} due follow-up(s) at {now_utc.isoformat()}")

        for row in due_rows:
            followup_id = row[0]
            lead_id     = row[1]
            channel     = row[2]
            msg_type    = row[3]
            name        = row[4] or "there"
            service     = row[5] or "our AI automation services"
            phone       = row[6] or ""

            # Build a warm, personalized follow-up message
            follow_up_text = (
                f"Hi {name}! 👋 I'm following up on your interest in {service}. "
                "I wanted to check if you had any questions or if you'd like to explore "
                "how Autexa can help your business. I'm here whenever you're ready!"
            )

            # Dispatch through the correct channel
            success = False
            try:
                if channel == "whatsapp" and phone:
                    # Send via WhatsApp outbound route in channels-service
                    resp = httpx.post(
                        f"{CHANNELS_SERVICE_URL}/webhook/whatsapp/send",
                        json={"phone": phone, "message": follow_up_text},
                        timeout=15.0,
                    )
                    resp.raise_for_status()
                    success = True
                else:
                    # Website widget: re-inject as a new agent chat message
                    # Using the lead's phone as sender_id (same as original)
                    resp = httpx.post(
                        f"{AGENT_SERVICE_URL}/api/chat",
                        json={
                            "channel": "website",
                            "sender_id": phone or f"followup-lead-{lead_id}",
                            "message": "[AUTOMATED FOLLOW-UP] " + follow_up_text,
                        },
                        timeout=30.0,
                    )
                    resp.raise_for_status()
                    success = True
            except Exception as e:
                print(f"[Worker] Failed to send follow-up {followup_id}: {e}")

            # Update the followup row status
            new_status = "sent" if success else "skipped"
            db.execute(
                text("UPDATE followups SET status = :status WHERE id = :id"),
                {"status": new_status, "id": followup_id}
            )

            # Write audit log entry (same pattern as ToolCallLog)
            db.execute(
                text("""
                    INSERT INTO tool_call_logs (lead_id, tool_name, arguments, result, created_at)
                    VALUES (:lead_id, :tool_name, CAST(:arguments AS jsonb), CAST(:result AS jsonb), NOW())
                """),
                {
                    "lead_id": lead_id,
                    "tool_name": "schedule_followup_sent",
                    "arguments": json.dumps({
                        "followup_id": followup_id,
                        "channel": channel,
                        "type": msg_type,
                    }),
                    "result": json.dumps({
                        "status": new_status,
                        "message": follow_up_text[:100] + "...",
                    }),
                }
            )

        db.commit()
        return {"processed": len(due_rows)}

    except Exception as e:
        db.rollback()
        print(f"[Worker] Error processing follow-ups: {e}")
        raise
    finally:
        db.close()
