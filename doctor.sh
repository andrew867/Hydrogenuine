#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"
export HG_GATEWAY_API_KEY="${HG_GATEWAY_API_KEY:-oss-demo-key}"
export HG_COMMUNITY_DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community}"

python --version
python -c "import hg_gateway.main; import hg_gateway.community; print('imports ok')"
python -m pytest tests/test_community_backend_acceptance.py -q
python -m pytest tests/test_public_packaging_docs.py -q

if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  echo "running api health: ok"
else
  echo "api health: not running"
fi
