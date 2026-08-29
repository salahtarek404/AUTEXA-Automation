"""
Instagram Graph API channel webhook.

Handles:
  GET  /webhook/{tenant_id}/instagram         — Meta's verification challenge
  POST /webhook/{tenant_id}/instagram         — Incoming message from Instagram DMs
  POST /webhook/{tenant_id}/instagram/send    — Internal outbound send (used by worker-service)

Design: fetch tenant config dynamically → normalize → forward to agent-service /api/chat.
"""

import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

router = APIRouter()

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8000")
INSTAGRAM_VERIFY_TOKEN_DEFAULT = os.getenv("INSTAGRAM_VERIFY_TOKEN", "autexa_instagram_verify_token")

INSTAGRAM_API_BASE = "https://graph.facebook.com/v18.0"


async def _fetch_tenant_config(tenant_id: str) -> dict:
    """Helper to fetch tenant config dynamically from agent-service."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{AGENT_SERVICE_URL}/api/tenants/{tenant_id}/config")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[Instagram] Error fetching config for tenant {tenant_id}: {e}")
    # Return defaults for backward compatibility/testing fallback
    return {
        "tenant_id": tenant_id,
        "instagram_verify_token": INSTAGRAM_VERIFY_TOKEN_DEFAULT,
        "instagram_access_token": ""
    }


@router.get("/webhook/{tenant_id}/instagram")
@router.get("/webhook/instagram")  # Backward compatibility
async def verify_instagram_webhook(
    tenant_id: str = "autexa",
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta's webhook verification handshake for Instagram.
    """
    config = await _fetch_tenant_config(tenant_id)
    verify_token = config.get("instagram_verify_token") or INSTAGRAM_VERIFY_TOKEN_DEFAULT

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print(f"[Instagram] Webhook verified successfully for tenant: {tenant_id}")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/webhook/{tenant_id}/instagram")
@router.post("/webhook/instagram")  # Backward compatibility
async def receive_instagram_message(request: Request, tenant_id: str = "autexa"):
    """
    Receives incoming Instagram webhook events.
    """
    body = await request.json()

    try:
        entry = body.get("entry", [{}])[0]
        messaging = entry.get("messaging", [])

        if not messaging:
            return {"status": "ok"}

        event = messaging[0]
        message = event.get("message", {})
        sender_id = event.get("sender", {}).get("id")

        if not sender_id or not message:
            return {"status": "ok"}

        text_body = message.get("text", "")
        if not text_body:
            return {"status": "ok"}

        print(f"[Instagram] [{tenant_id}] Received from {sender_id}: {text_body}")

        config = await _fetch_tenant_config(tenant_id)
        access_token = config.get("instagram_access_token")

        # Normalize and forward to agent-service with tenant_id
        payload = {
            "channel": "instagram",
            "sender_id": sender_id,
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

                # Send bot reply back to Instagram
                if bot_reply and access_token:
                    await _send_instagram_message(sender_id, bot_reply, access_token)

            except Exception as e:
                print(f"[Instagram] Error forwarding to agent-service: {e}")

        return {"status": "ok"}

    except Exception as e:
        print(f"[Instagram] Error parsing webhook payload: {e}")
        return {"status": "ok"}


@router.post("/webhook/{tenant_id}/instagram/send")
@router.post("/webhook/instagram/send")  # Backward compatibility
async def send_instagram_outbound(request: Request, tenant_id: str = "autexa"):
    """
    Internal endpoint used to send outbound messages via Instagram.
    """
    data = await request.json()
    recipient_id = data.get("recipient_id") or data.get("phone")
    message = data.get("message")

    if not recipient_id or not message:
        raise HTTPException(status_code=400, detail="Missing recipient_id or message.")

    config = await _fetch_tenant_config(tenant_id)
    access_token = config.get("instagram_access_token")

    if not access_token:
        return {
            "status": "skipped",
            "message": f"Instagram credentials not configured for tenant {tenant_id}.",
        }

    try:
        await _send_instagram_message(recipient_id, message, access_token)
        return {"status": "sent", "recipient_id": recipient_id, "tenant_id": tenant_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send Instagram: {e}")


async def _send_instagram_message(to_id: str, text: str, token: str):
    """Calls the Instagram Messages API to send a DMs response."""
    url = f"{INSTAGRAM_API_BASE}/me/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": to_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        print(f"[Instagram] Sent message to {to_id}: status {resp.status_code}")
