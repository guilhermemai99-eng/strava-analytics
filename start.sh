#!/bin/sh
set -eu
npx prisma migrate deploy
npx next start --hostname 0.0.0.0 --port "${PORT:-3000}"
