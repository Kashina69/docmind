#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "missing server/.env"; exit 1; }
mkdir -p storage
[ -x venv/bin/uvicorn ] || ./venv/bin/pip install -r requirements.lock

PORT="${PORT:-8000}"
exec ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
