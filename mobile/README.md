# Pulse Mobile (Expo)

Expo Go shell for the Pulse web app. Does **not** replace the FastAPI/static web client in the repo root — it wraps it in a native WebView for iPhone/Android testing.

## Prerequisites

- [Expo Go](https://expo.dev/go) on your phone
- Node 18+

## Commands

```bash
cd mobile
npm install
npm run start          # LAN (same Wi‑Fi)
npm run start:tunnel   # Tunnel — use this for physical iPhone on another network
```

Scan the QR code with the iPhone Camera app or Expo Go.

## Backend URL

Default: production Pulse (`/dashboard`).

Override for local backend (must be reachable from the phone — use a public tunnel, not `localhost`):

```bash
EXPO_PUBLIC_PULSE_URL=https://your-tunnel.example/dashboard npm run start:tunnel
```

## Project layout

- `App.tsx` — WebView shell
- `app.config.js` — Expo config + `extra.pulseUrl`
- Web app remains at repo root (`static/`, `main.py`, etc.)
