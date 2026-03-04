# House 88 – Omnichannel Chatroom (WhatsApp / WeChat / Facebook / IG)

This project is now centered on an **Omnichat-style unified inbox**:

- One backend for **WhatsApp, WeChat, Facebook, Instagram**
- **Chatroom-based architecture** (each channel/account/page = a chatroom)
- Unified inbox flow: **chatroom → thread → messages**
- **Per-chatroom AI controls**:
  - AI auto-reply
  - working schedule
  - one-click AI pause

> Existing lead/CRM endpoints remain in repo as legacy MVP modules, but the new core is `/omni/*`.

---

## Tech Stack

- Python 3.11+
- FastAPI + SQLAlchemy + SQLite (default)
- React 19 + Vite 7 frontend dashboard
- Pytest

---

## Quick Start

### Backend

```bash
python3 -m pip install -e ".[dev]"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend default: `http://localhost:5173`  
Backend default: `http://localhost:8000`

---

## Omnichannel API (`/omni/*`)

### Chatrooms

- `GET /omni/chatrooms?channel=...`
- `POST /omni/chatrooms`

Each chatroom tracks:
- `channel` (`whatsapp|wechat|facebook|instagram`)
- `external_room_id` (e.g. phone_number_id / page_id / account_id)
- `ai_enabled`
- `ai_schedule_start`, `ai_schedule_end`, `timezone`

### Per-chatroom AI control

- `GET /omni/chatrooms/{chatroom_id}/ai`
- `PUT /omni/chatrooms/{chatroom_id}/ai/status`
- `POST /omni/chatrooms/{chatroom_id}/ai/pause`
- `PUT /omni/chatrooms/{chatroom_id}/ai/schedule`

### Unified inbox

- `GET /omni/chatrooms/{chatroom_id}/threads`
- `GET /omni/threads/{thread_id}/messages`
- `POST /omni/threads/{thread_id}/messages` (agent/system outbound)

### Inbound webhooks / simulation

- `POST /omni/webhooks/{channel}`
- `POST /omni/simulate`

Simulation payload:

```json
{
  "channel": "whatsapp",
  "chatroom_external_id": "house88-whatsapp",
  "contact_id": "wa-user-001",
  "contact_name": "Alex",
  "text": "想問價錢"
}
```

---

## Frontend Dashboard

Current React UI includes:

- Chatroom list across all channels
- Thread list for selected chatroom
- Message timeline + manual outbound send
- Per-chatroom AI toggle / pause / schedule
- Inbound simulator for WhatsApp/WeChat/Facebook/IG
- Create new chatroom UI

---

## Tests

```bash
python3 -m pytest -q
```

Current suite includes omnichannel tests:
- seeded chatrooms for all 4 channels
- per-chatroom AI pause isolation
- thread/message flow and manual outbound send
- chatroom schedule update

---

## Next production steps

- Channel signature verification (Meta/WeChat)
- OAuth/token management per channel account
- Role-based access control for agent/admin
- Real-time updates (WebSocket) + unread counters
- Queue workers for outbound retries and webhook fan-out
