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

Profile photos are written to `public/uploads/avatars/{userId}/{generation}/` as WebP sizes (`w64`, `w128`, `w256`, `w512`). `User.avatarUrl` stores that folder path (or a Google photo URL), never the image bytes. A new generation folder is created on each upload so browsers do not keep a stale photo.

## Stack

Next.js (App Router) · TypeScript · PostgreSQL · Prisma

Business logic lives in `lib/services`. Route handlers are thin. Secrets stay on the server.

## Railway

Production deploys from GitHub, not from `railway up`.

1. The web service is connected to this GitHub repo.
2. A push (or merge) to the branch Railway watches triggers Nixpacks.
3. `railway.toml` / `Procfile` start with `prisma migrate deploy && next start`.
4. Set `DATABASE_URL`, `AUTH_SECRET`, and `APP_URL` in the Railway dashboard. Never commit those values.

If a push does not deploy, the GitHub integration or the watched branch is wrong in Railway → Settings. That cannot be changed from this repo.
