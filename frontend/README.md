# House 88 Omnichannel Frontend

React + Vite frontend for the House 88 omnichannel chatroom backend.

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

- Chatroom list (WhatsApp / WeChat / Facebook / Instagram)
- Thread list per chatroom
- Message timeline + manual outbound send
- Per-chatroom AI control (toggle / pause / schedule)
- Inbound simulator
- Chatroom creation
