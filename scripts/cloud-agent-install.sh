#!/usr/bin/env bash
set -euo pipefail

cd /workspace

if command -v pg_ctlcluster >/dev/null 2>&1; then
  sudo pg_ctlcluster 16 main start || true
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='pulse'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER pulse WITH PASSWORD 'pulse' SUPERUSER;"
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='pulse'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE pulse OWNER pulse;"
fi

if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

npx prisma generate
npx prisma migrate deploy
