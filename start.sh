#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
fi

set -a
# shellcheck source=/dev/null
. ./.env
set +a

export HG_GATEWAY_API_KEY="${HG_GATEWAY_API_KEY:-oss-demo-key}"
export HG_COMMUNITY_DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"

if [ ! -d .venv ]; then
  python -m venv .venv
fi

PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e ".[dev]"

RUN_DIR="$HG_COMMUNITY_DATA_DIR/run"
mkdir -p "$RUN_DIR"

"$PYTHON" -m uvicorn hg_gateway.main:app --host 127.0.0.1 --port 8000 &
echo "$!" > "$RUN_DIR/api.pid"

(cd community_ui && "$PYTHON" -m http.server 4173 --bind 127.0.0.1) &
echo "$!" > "$RUN_DIR/ui.pid"

echo "Hydrogenuine Community is starting."
echo "UI:  http://127.0.0.1:4173"
echo "API: http://127.0.0.1:8000/healthz"
echo "API key: $HG_GATEWAY_API_KEY"
echo "Stop: ./stop.sh"
