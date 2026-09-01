# Pulse Mobile (Expo)

Expo Go shell for the Pulse web app. Does **not** replace the FastAPI/static web client in the repo root — it wraps it in a native WebView for iPhone/Android testing.

## Prerequisites

- [Expo Go](https://expo.dev/go) from the **Apple App Store / Google Play** (SDK **54**)
- Node 18+

This shell stays on SDK 54 so store Expo Go can open it. SDK 55+ is not in the App Store; those versions need [sign.expo.dev](https://sign.expo.dev) or `eas go`.

## Commands

```bash
cd mobile
npm install
npm run start          # LAN (same Wi‑Fi as your Mac)
npm run start:tunnel   # Expo ngrok tunnel (works on Mac; may fail on some cloud VMs)
```

**iPhone (Expo Go):** use tunnel mode so Metro is reachable from your phone:

```bash
cd mobile && npm run start:tunnel
```

Scan the QR code with the iPhone Camera or Expo Go.

If `--tunnel` fails (ngrok blocked), run Metro with a public reverse proxy hostname, e.g. [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/):

```bash
cloudflared tunnel --url http://127.0.0.1:8081
# copy the https://….trycloudflare.com host, then:
REACT_NATIVE_PACKAGER_HOSTNAME=YOUR_HOST.trycloudflare.com \
EXPO_PACKAGER_PROXY_URL=https://YOUR_HOST.trycloudflare.com \
npx expo start --port 8081
```

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
