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

- `/chatrooms` – chatroom list, filter, creation
- `/inbox/:chatroomId` – thread list + messages + manual outbound send
- `/ai-settings` – per-chatroom AI toggle / pause / schedule + integration keys/tokens
- `/simulator` – inbound simulator for WhatsApp / WeChat / Facebook / Instagram

The app uses **React Router** and a persistent sidebar navigation.
