"""Execute kind=dag cron payloads via run_dag_job.py (no agentTurn LLM wrapper)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .dag_payload import DagCronPayload, parse_dag_payload


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return Path.cwd()


def execute_dag_job(payload: DagCronPayload | dict[str, Any], *, workspace: Path | None = None) -> dict[str, Any]:
    parsed = payload if isinstance(payload, DagCronPayload) else parse_dag_payload(payload)
    if parsed is None:
        return {"ok": False, "error": "invalid dag payload"}

    root = workspace or _workspace_root()
    script = root / "scripts" / "run_dag_job.py"
    if not script.exists():
        return {"ok": False, "error": f"run_dag_job.py not found at {script}"}

    cmd = [sys.executable, str(script), "--job-id", parsed.job_id]
    for key, value in parsed.inputs.items():
        cmd.extend(["--input", f"{key}={value}"])

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=parsed.timeout_seconds,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    result: dict[str, Any] = {"ok": proc.returncode == 0, "job_id": parsed.job_id, "returncode": proc.returncode}
    if stdout:
        try:
            result["summary"] = json.loads(stdout)
        except json.JSONDecodeError:
            result["stdout"] = stdout[-4000:]
    if stderr:
        result["stderr"] = stderr[-2000:]
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Execute a native DAG cron job by id.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--input", action="append", default=[], help="KEY=VALUE (repeatable)")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    inputs: dict[str, str] = {}
    for item in args.input:
        if "=" in item:
            k, _, v = item.partition("=")
            inputs[k.strip()] = v.strip()

    payload = DagCronPayload(job_id=args.job_id, inputs=inputs, timeout_seconds=args.timeout_seconds)
    result = execute_dag_job(payload)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
