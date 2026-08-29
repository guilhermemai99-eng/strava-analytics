#!/usr/bin/env bash
set -euo pipefail

cd /workspace

# Ensure local Postgres is up for Cloud Agents (idempotent).
if command -v pg_ctlcluster >/dev/null 2>&1; then
  sudo pg_ctlcluster 16 main start || true
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='strava'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER strava WITH PASSWORD 'strava' SUPERUSER;"
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='strava_analytics'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE strava_analytics OWNER strava;"
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://strava:strava@localhost:5432/strava_analytics}"

# shellcheck disable=SC1091
source .venv/bin/activate
alembic upgrade head
