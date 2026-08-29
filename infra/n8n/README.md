# n8n Hot Lead Notification — Setup Guide

This directory contains the n8n workflow for sending hot-lead alerts to Slack.

## Quickstart

1. **Start the stack:**
   ```bash
   docker compose up -d n8n
   ```

2. **Open n8n UI:** http://localhost:5678  
   Login: `admin` / `autexa_n8n` (or values from `.env`)

3. **Import the workflow:**
   - Go to **Workflows → Import from File**
   - Select `workflows/hot_lead_notification.json`
   - Click **Import**

4. **Configure Slack:**
   - In the imported workflow, click the **"Send Slack Alert"** node
   - The node uses `{{ $env.SLACK_WEBHOOK_URL }}` — set this in n8n:
     - Go to **Settings → External Secrets** (or edit the node directly)
     - OR hardcode your Slack webhook URL in the node's URL field
   - Get a Slack webhook URL at: https://api.slack.com/messaging/webhooks

5. **Activate the workflow:** Toggle it to **Active** in the n8n UI.

6. **Set the webhook URL in your stack's `.env`:**
   ```env
   N8N_WEBHOOK_URL=http://n8n:5678/webhook/hot-lead
   ```
   Restart `agent-service` after changing this.

## How it works

```
qualify_lead(priority=hot)
  → tools.py auto-calls notify_sales_team()
    → POST http://n8n:5678/webhook/hot-lead  {lead details}
      → n8n formats message
        → POST to Slack Incoming Webhook
          → #sales-alerts channel receives: "🔥 HOT LEAD ALERT: ..."
```

## Testing the webhook manually

```bash
curl -X POST http://localhost:5678/webhook/hot-lead \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "name": "Test Lead",
    "email": "test@example.com",
    "phone": "+1234567890",
    "business_type": "gym",
    "service_requested": "WhatsApp automation",
    "intent": "buying",
    "priority": "hot",
    "source": "website"
  }'
```
