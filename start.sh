#!/bin/sh
set -e
echo "[start] Running database migrations..."
alembic upgrade head
echo "[start] Starting uvicorn..."
# Cap graceful shutdown so Railway can finish "Tidying up previous deployment"
# instead of waiting forever on keep-alive connections to the old replica.
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --timeout-keep-alive 5 \
  --timeout-graceful-shutdown 15
