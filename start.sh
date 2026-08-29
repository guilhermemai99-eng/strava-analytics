#!/bin/sh
set -e
echo "[start] Running database migrations..."
alembic upgrade head
echo "[start] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
