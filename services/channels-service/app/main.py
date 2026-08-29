from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
import os
import pathlib

from app.whatsapp import router as whatsapp_router

app = FastAPI(title="Channels Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8000")

# Mount WhatsApp channel routes
app.include_router(whatsapp_router)


@app.post("/webhook/widget")
async def widget_webhook(request: Request):
    """
    Receives payload from the website widget, normalizes it, and sends to the agent-service.
    """
    data = await request.json()
    sender_id = data.get("sender_id")
    message = data.get("message")

    if not sender_id or not message:
        raise HTTPException(status_code=400, detail="Missing sender_id or message")

    payload = {
        "channel": "website",
        "sender_id": sender_id,
        "message": message
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{AGENT_SERVICE_URL}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error calling agent-service: {e}")
            raise HTTPException(status_code=500, detail="Agent service unavailable")


widget_dir = pathlib.Path(__file__).parent / "widget"
widget_dir.mkdir(exist_ok=True)
app.mount("/widget", StaticFiles(directory=str(widget_dir), html=True), name="widget")


@app.get("/")
def root():
    return {"message": "Channels Service is running. Visit /widget for the demo."}
