# Autexa AI Automation System - Phase 1 Architecture

## Overview

The Autexa system is designed as a modular monorepo to ensure scalability and maintainability as we move from a simple prototype (Phase 1) to a full-fledged enterprise tool (Phase 2+).

In Phase 1, the architecture is stripped down to the essentials to prove the fundamental flow:
`Website Widget -> Channels Service -> Agent Service -> Gemini LLM -> Database -> Dashboard`

## Components

### 1. `agent-service` (FastAPI)
The "Brain" of the application.
- **Port:** 8000
- **Responsibilities:**
  - Connects to the PostgreSQL database using SQLAlchemy.
  - Exposes REST APIs for the dashboard and for inbound webhooks.
  - Communicates directly with the LLM (Google Gemini 1.5 Flash in Phase 1) via the `llm_client.py` wrapper. By confining the LLM logic here, we can easily swap to Claude or add RAG tools in later phases with 1-line changes.
- **Key Endpoints:** 
  - `POST /api/chat`: Receives a message, updates/creates the Lead and Conversation models, talks to the LLM, and persists the response.
  - `GET /api/leads`: Exposes the leads table to the dashboard.

### 2. `channels-service` (FastAPI)
The "Middleware".
- **Port:** 8001
- **Responsibilities:**
  - Sits at the edge to receive incoming events from various channels (Website, WhatsApp, Instagram).
  - Normalizes payloads into a standard format and proxies them over HTTP to the `agent-service`.
- **Key Endpoints:**
  - `POST /webhook/widget`: The endpoint the frontend demo widget talks to.
  - `GET /widget`: Hosts the simple standalone HTML chat widget for testing.

### 3. `apps/dashboard` (React + Vite)
The "Admin UI".
- **Port:** 5173
- **Responsibilities:**
  - A lightweight Single Page Application styled with TailwindCSS.
  - Fetches and displays a read-only list of leads from `agent-service`.

### 4. PostgreSQL (Docker)
- **Port:** 5432
- **Responsibilities:**
  - Relational layout featuring `leads` and `conversations`. The `conversations` table uses JSONB to store the raw message history arrays efficiently.

## How to Run Locally

1. **Environment Variables**: Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY`.
2. **Start Backend Stack**: Run `docker-compose up -d --build`. This will start the Database, `agent-service`, and `channels-service`. (Note: The first run dynamically creates the DB tables).
3. **Start Dashboard**: 
   - `cd apps/dashboard`
   - `npm install`
   - `npm run dev`
4. **Test the Flow**: 
   - Open `http://localhost:8001/widget` in a browser and send a message. You will get a response from Gemini.
   - Open `http://localhost:5173` in a browser to view the Dashboard. You will see the new lead generated from the widget interaction.
