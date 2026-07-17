from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from hg_core.task_graph.native_task_tools import run_task_tool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a task tool inside the task sandbox child process.")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser.parse_args()


def _load_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    args = _parse_args()
    payload = _load_payload()
    resolved_inputs = payload.get("resolved_inputs")
    if not isinstance(resolved_inputs, dict):
        resolved_inputs = {}
    result = run_task_tool(args.task_name, resolved_inputs, timeout_s=args.timeout_s)
    if result is None:
        result = {"ok": False, "error": f"unhandled task: {args.task_name}", "returncode": -1}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
    sys.stdout.flush()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
