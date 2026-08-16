#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"
export HG_COMMUNITY_DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community}"
export HG_CONFIG_PATH="${HG_CONFIG_PATH:-$HG_COMMUNITY_DATA_DIR/config.json}"
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python; fi

"$PYTHON" --version
"$PYTHON" -m hg_cli doctor --config "$HG_CONFIG_PATH" --self-test

if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  echo "running api health: ok"
else
  echo "api health: not running"
fi
