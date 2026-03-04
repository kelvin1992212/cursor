# House 88 Dashboard Frontend

React + Vite frontend for the House 88 WhatsApp AI Lead Engine backend.

## Run locally

```bash
cp .env.example .env
npm install
npm run dev
```

By default the frontend calls:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Build and lint

```bash
npm run lint
npm run build
```

## Main screens

- AI Control Center (enable/disable, one-click pause, schedule)
- Webhook Simulator (send WhatsApp/WeChat test messages)
- Leads list + filters
- Customer detail + tags
- Booking management
- Lead reports + AI feedback
- Agent management
