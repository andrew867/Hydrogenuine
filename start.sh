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

export HG_COMMUNITY_DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community}"
export HG_CONFIG_PATH="${HG_CONFIG_PATH:-$HG_COMMUNITY_DATA_DIR/config.json}"
export HG_GATEWAY_AUTH_MODE="${HG_GATEWAY_AUTH_MODE:-local-no-key}"
export HG_GATEWAY_STORE="${HG_GATEWAY_STORE:-sqlite}"
if [ "$HG_GATEWAY_STORE" = "memory" ]; then export HG_GATEWAY_STORE=sqlite; fi
export HG_GATEWAY_DB_PATH="${HG_GATEWAY_DB_PATH:-$HG_COMMUNITY_DATA_DIR/gateway.sqlite3}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"

if [ ! -d .venv ]; then
  python -m venv .venv
fi

PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e ".[dev]"

if [ ! -f "$HG_CONFIG_PATH" ]; then
  "$PYTHON" -m hg_cli init --mode demo --non-interactive --config "$HG_CONFIG_PATH" --data-dir "$HG_COMMUNITY_DATA_DIR"
fi

RUN_DIR="$HG_COMMUNITY_DATA_DIR/run"
mkdir -p "$RUN_DIR"

"$PYTHON" -m uvicorn hg_gateway.main:app --host 127.0.0.1 --port 8000 &
echo "$!" > "$RUN_DIR/api.pid"

(cd community_ui && "$PYTHON" -m http.server 4173 --bind 127.0.0.1) &
echo "$!" > "$RUN_DIR/ui.pid"

echo "Hydrogenuine Community is starting."
echo "UI:  http://127.0.0.1:4173"
echo "API: http://127.0.0.1:8000/healthz"
echo "Mode: local demo/mock (no API keys required)"
echo "Check: ./.venv/bin/hg doctor --self-test"
echo "Stop: ./stop.sh"
