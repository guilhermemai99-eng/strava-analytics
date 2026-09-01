# PULSE

Find your pace. Find your people.

A social-first running app. Not an analytics dashboard.

## Local setup

1. PostgreSQL 16 running, database `pulse` owned by user `pulse` (password `pulse`).
   Cloud agents use the scripts in `scripts/`. Docker: `docker compose up -d`.
2. Copy `.env.example` to `.env` and set `AUTH_SECRET`.
3. `npm install`
4. `npx prisma migrate dev`
5. `npm run db:seed` (optional demo users)
6. `npm run dev` — http://localhost:3000

Demo seed login: `joana@pulse.run` / `pulse1234`

Google and Apple sign-in need the OAuth variables in `.env.example`. Redirect URIs are `{APP_URL}/api/auth/google/callback` and `{APP_URL}/api/auth/apple/callback`.

## Stack

Next.js (App Router) · TypeScript · PostgreSQL · Prisma

Business logic lives in `lib/services`. Route handlers are thin. Secrets stay on the server.
