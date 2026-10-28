#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

[ -f "$ROOT/server/.env" ] || { echo "missing server/.env"; exit 1; }
[ -f "$ROOT/client/.env" ] || { echo "missing client/.env"; exit 1; }

if [ ! -d "$ROOT/server/venv" ]; then
  python3.11 -m venv "$ROOT/server/venv"
fi
if [ ! -x "$ROOT/server/venv/bin/uvicorn" ]; then
  "$ROOT/server/venv/bin/pip" install -r "$ROOT/server/requirements.lock"
fi
if [ ! -d "$ROOT/client/node_modules" ]; then
  (cd "$ROOT/client" && npm install)
fi

"$ROOT/server/start_server.sh" &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT INT TERM

for _ in $(seq 1 30); do
  curl -sf http://localhost:8000/ >/dev/null 2>&1 && break
  sleep 1
done

cd "$ROOT/client"
exec npm run dev
