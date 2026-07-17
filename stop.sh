#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${HG_COMMUNITY_DATA_DIR:-$ROOT/.hg_community}"
RUN_DIR="$DATA_DIR/run"

for name in api.pid ui.pid; do
  path="$RUN_DIR/$name"
  if [ -f "$path" ]; then
    pid="$(cat "$path")"
    if [ -n "$pid" ]; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$path"
  fi
done

echo "Hydrogenuine Community services stopped."
