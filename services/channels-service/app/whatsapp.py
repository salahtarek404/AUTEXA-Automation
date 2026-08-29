"""
WhatsApp Cloud API channel webhook.

Handles:
  GET  /webhook/whatsapp         — Meta's verification challenge
  POST /webhook/whatsapp         — Incoming message from WhatsApp sandbox
  POST /webhook/whatsapp/send    — Internal outbound send (used by worker-service)

Design: normalize → forward to agent-service /api/chat (zero changes to agent-service).
"""

import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

router = APIRouter()

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "autexa_verify_token")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta's webhook verification handshake.
    Returns the challenge string if the verify token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        print(f"[WhatsApp] Webhook verified successfully.")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(request: Request):
    """
    Receives incoming WhatsApp Cloud API webhook events.
    Normalizes the payload and forwards to agent-service — same pattern as widget.
    """
    body = await request.json()

    try:
        # Navigate the WhatsApp Cloud API payload structure
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Status update or non-message event — acknowledge and ignore
            return {"status": "ok"}

        message = messages[0]
        msg_type = message.get("type", "")

        if msg_type != "text":
            # Only handle text messages for now
            print(f"[WhatsApp] Ignoring non-text message type: {msg_type}")
            return {"status": "ok"}

        sender_phone = message["from"]
        text_body = message["text"]["body"]
        message_id = message.get("id", "")

        print(f"[WhatsApp] Received from {sender_phone}: {text_body}")

        # Normalize and forward to agent-service (zero agent-service changes)
        payload = {
            "channel": "whatsapp",
            "sender_id": sender_phone,
            "message": text_body,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                agent_resp = await client.post(
                    f"{AGENT_SERVICE_URL}/api/chat", json=payload
                )
                agent_resp.raise_for_status()
                reply_data = agent_resp.json()
                bot_reply = reply_data.get("reply", "")

                # Send bot reply back to WhatsApp
                if bot_reply and WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
                    await _send_whatsapp_message(sender_phone, bot_reply)

            except Exception as e:
                print(f"[WhatsApp] Error forwarding to agent-service: {e}")

        # Always return 200 to WhatsApp to acknowledge receipt
        return {"status": "ok"}

    except Exception as e:
        print(f"[WhatsApp] Error parsing webhook payload: {e}")
        return {"status": "ok"}  # Still return 200 to avoid Meta retries


@router.post("/webhook/whatsapp/send")
async def send_whatsapp_outbound(request: Request):
    """
    Internal endpoint used by worker-service to send follow-up messages via WhatsApp.
    Body: { "phone": "15551234567", "message": "Hi, following up..." }
    """
    data = await request.json()
    phone = data.get("phone")
    message = data.get("message")

    if not phone or not message:
        raise HTTPException(status_code=400, detail="Missing phone or message.")

    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return {
            "status": "skipped",
            "message": "WhatsApp credentials not configured — message not sent.",
        }

    try:
        await _send_whatsapp_message(phone, message)
        return {"status": "sent", "phone": phone}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp message: {e}")


async def _send_whatsapp_message(to_phone: str, text: str):
    """Calls the WhatsApp Cloud API to send a text message."""
    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        print(f"[WhatsApp] Sent message to {to_phone}: status {resp.status_code}")
