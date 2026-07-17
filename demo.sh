#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"
export HG_GATEWAY_API_KEY="${HG_GATEWAY_API_KEY:-oss-demo-key}"
export HG_COMMUNITY_DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community_demo}"
export HG_GATEWAY_STORE=memory

python examples/offline_demo.py
