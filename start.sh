#!/bin/sh
set -eu
cd "$(dirname "$0")"
npx prisma migrate deploy
npx next start --hostname 0.0.0.0 --port "${PORT:-3000}"
