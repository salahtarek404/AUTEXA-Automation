"""
WhatsApp Cloud API channel webhook.

Handles:
  GET  /webhook/{tenant_id}/whatsapp         — Meta's verification challenge
  POST /webhook/{tenant_id}/whatsapp         — Incoming message from WhatsApp sandbox
  POST /webhook/{tenant_id}/whatsapp/send    — Internal outbound send (used by worker-service)

Design: fetch tenant config dynamically → normalize → forward to agent-service /api/chat.
"""

import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

router = APIRouter()

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
WHATSAPP_VERIFY_TOKEN_DEFAULT = os.getenv("WHATSAPP_VERIFY_TOKEN", "autexa_verify_token")

WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


async def _fetch_tenant_config(tenant_id: str) -> dict:
    """Helper to fetch tenant config dynamically from agent-service."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{AGENT_SERVICE_URL}/api/tenants/{tenant_id}/config")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[WhatsApp] Error fetching config for tenant {tenant_id}: {e}")
    # Return defaults for backward compatibility/testing fallback
    return {
        "tenant_id": tenant_id,
        "whatsapp_verify_token": WHATSAPP_VERIFY_TOKEN_DEFAULT,
        "whatsapp_access_token": "",
        "whatsapp_phone_number_id": ""
    }


@router.get("/webhook/{tenant_id}/whatsapp")
@router.get("/webhook/whatsapp")  # Backward compatibility for tenant zero
async def verify_whatsapp_webhook(
    tenant_id: str = "autexa",
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta's webhook verification handshake.
    """
    config = await _fetch_tenant_config(tenant_id)
    verify_token = config.get("whatsapp_verify_token") or WHATSAPP_VERIFY_TOKEN_DEFAULT
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print(f"[WhatsApp] Webhook verified for tenant: {tenant_id}")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/webhook/{tenant_id}/whatsapp")
@router.post("/webhook/whatsapp")  # Backward compatibility for tenant zero
async def receive_whatsapp_message(request: Request, tenant_id: str = "autexa"):
    """
    Receives incoming WhatsApp Cloud API webhook events.
    """
    body = await request.json()

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        message = messages[0]
        msg_type = message.get("type", "")

        if msg_type != "text":
            print(f"[WhatsApp] Ignoring non-text message type: {msg_type}")
            return {"status": "ok"}

        sender_phone = message["from"]
        text_body = message["text"]["body"]

        print(f"[WhatsApp] [{tenant_id}] Received from {sender_phone}: {text_body}")

        # Fetch credentials dynamically
        config = await _fetch_tenant_config(tenant_id)
        access_token = config.get("whatsapp_access_token")
        phone_number_id = config.get("whatsapp_phone_number_id")

        # Forward payload including tenant_id
        payload = {
            "channel": "whatsapp",
            "sender_id": sender_phone,
            "message": text_body,
            "tenant_id": tenant_id
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                agent_resp = await client.post(
                    f"{AGENT_SERVICE_URL}/api/chat", json=payload
                )
                agent_resp.raise_for_status()
                reply_data = agent_resp.json()
                bot_reply = reply_data.get("reply", "")

                # Send reply back via Meta APIs
                if bot_reply and access_token and phone_number_id:
                    await _send_whatsapp_message(sender_phone, bot_reply, access_token, phone_number_id)

            except Exception as e:
                print(f"[WhatsApp] Error forwarding to agent-service: {e}")

        return {"status": "ok"}

    except Exception as e:
        print(f"[WhatsApp] Error parsing webhook payload: {e}")
        return {"status": "ok"}


@router.post("/webhook/{tenant_id}/whatsapp/send")
@router.post("/webhook/whatsapp/send")  # Backward compatibility
async def send_whatsapp_outbound(request: Request, tenant_id: str = "autexa"):
    """
    Internal endpoint used by worker-service.
    """
    data = await request.json()
    phone = data.get("phone")
    message = data.get("message")

    if not phone or not message:
        raise HTTPException(status_code=400, detail="Missing phone or message.")

    config = await _fetch_tenant_config(tenant_id)
    access_token = config.get("whatsapp_access_token")
    phone_number_id = config.get("whatsapp_phone_number_id")

    if not access_token or not phone_number_id:
        return {
            "status": "skipped",
            "message": f"WhatsApp credentials not configured for tenant {tenant_id}.",
        }

    try:
        await _send_whatsapp_message(phone, message, access_token, phone_number_id)
        return {"status": "sent", "phone": phone, "tenant_id": tenant_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp: {e}")


async def _send_whatsapp_message(to_phone: str, text: str, token: str, phone_id: str):
    url = f"{WHATSAPP_API_BASE}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
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
