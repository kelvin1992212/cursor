# House 88 – WhatsApp AI System (First Phase MVP, Python)

Python backend MVP for **House 88 WhatsApp AI Lead Engine** using **FastAPI + SQLite + SQLAlchemy**.

This implementation focuses on your First Phase requirements:

1. WhatsApp/Webhook integration + multi-agent shared inbox model  
2. AI auto-reply with schedule + one-click pause  
3. AI → human handover on high-intent triggers  
4. Auto/manual lead tagging  
5. Booking flow and calendar slot suggestions  
6. Basic CRM (customers, chats, tags, filters)  
7. AI feedback/data collection foundation for ongoing optimization  
8. Auto lead report generation after handover

---

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- SQLite (default; replaceable by PostgreSQL/MySQL)
- Pytest
- React 19 + Vite 7 (Admin/CRM frontend)

---

## Quick Start (Backend)

```bash
python3 -m pip install -e ".[dev]"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

---

## Quick Start (Frontend Dashboard)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`  
API target is controlled by `VITE_API_BASE_URL` (default `http://localhost:8000`).

The React dashboard includes:
- AI status toggle / pause / schedule
- Leads list + filters
- Customer detail + tag management
- Booking creation + booking list
- Lead report viewer + AI feedback submit
- Webhook simulator (WhatsApp/WeChat inbound test)

---

## Core API Endpoints

### 1) Webhooks / Inbound Messages

- `GET /webhooks/whatsapp`  
  WhatsApp Cloud API verification (`hub.mode`, `hub.challenge`, `hub.verify_token`)

- `POST /webhooks/whatsapp`  
  Receive WhatsApp inbound payload (supports simple payload and Cloud API style payload)

- `POST /webhooks/wechat`  
  Receive WeChat inbound payload (simple payload)

- `POST /webhooks/simulate`  
  Development/testing endpoint with normalized message schema:

```json
{
  "channel": "whatsapp",
  "phone": "+85261111111",
  "name": "Chris",
  "text": "想知按揭資訊"
}
```

### 2) Admin Dashboard APIs

- `GET /admin/ai/status`  
- `PUT /admin/ai/status` (enable/disable AI)  
- `POST /admin/ai/pause` (one-click pause AI)  
- `PUT /admin/ai/schedule` (e.g. 20:00–09:00 auto-reply window)  
- `POST /admin/agents`  
- `GET /admin/agents`  
- `POST /admin/properties/sync` (sync website listing data into internal KB)  
- `GET /admin/reports/{phone}` (lead reports)

### 3) CRM APIs

- `GET /crm/leads?tag=&property_code=&intent_stage=&from_date=&to_date=`  
- `GET /crm/customers/{phone}`  
- `POST /crm/customers/{phone}/tags`  
- `DELETE /crm/customers/{phone}/tags/{tag_name}`  
- `POST /crm/bookings`  
- `GET /crm/bookings`  
- `POST /crm/feedback` (AI response feedback: `correct` / `improve`)

---

## Mapping to First Phase Requirements

### 1️⃣ WhatsApp 系統整合
- Webhook verification + inbound processing ready
- Channel gateway abstraction supports WhatsApp/WeChat
- Multi-agent sharing handled via common lead pool + round-robin assignment
- Property sync endpoint allows website data ingestion and auto-send cards/links

### 2️⃣ AI 自動回覆（24/7）
- AI reply engine with natural language intent routing
- FAQ + listing lookup + property card response
- AI schedule control (`/admin/ai/schedule`)
- One-click pause (`/admin/ai/pause`)

### 3️⃣ AI → 真人 Agent 接手
- Trigger keywords (e.g. 想同真人傾 / 想約睇樓 / 即時報價)
- AI handover stops automation and assigns active agent
- Customer context, tags, and report generated automatically

### 4️⃣ Tag / 客戶標籤
- Auto tags from intent and budget extraction
- Manual tag management via CRM endpoints

### 5️⃣ Booking / 預約
- AI suggests slots when booking intent is detected
- Booking creation endpoint with customer + optional property + agent link
- Confirmation message auto-sent

### 6️⃣ Basic CRM
- Customer profile, chat history, tags, intent/follow-up status
- Lead listing and filters by tag/property/date/intent stage

### 7️⃣ AI Model Training（持續優化）
- Conversation data stored in DB
- AI feedback endpoint (`correct` / `improve`) for future retraining loops

### 8️⃣ AI Lead Report
- Auto lead report generated on handover
- Includes phone, intent stage, budget, tags, conversation summary

---

## Tests

```bash
python3 -m pytest -q
```

Current suite validates:
- AI auto reply
- AI pause behavior
- Handover + report generation
- Auto tagging + lead filtering
- Booking API flow

---

## Suggested Next Step (Phase 1.1 Production Hardening)

- Add real WhatsApp Cloud API send/receive signature verification
- Add auth/RBAC for Admin Dashboard APIs
- Replace SQLite with managed PostgreSQL
- Integrate real Google Calendar (OAuth + two-way sync)
- Add WhatsApp Flows payload templates and callback handling
- Add queue/worker for async notifications (Celery/RQ)
