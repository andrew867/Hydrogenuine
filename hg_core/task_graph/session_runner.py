"""
Session-runner integration for DAG agent nodes.

When HG_DAG_USE_SESSION_RUNNER and HG_SESSION_RUNNER_CMD are set,
dispatch can run agent nodes via the external session runner (e.g. hg cron run)
instead of only emitting run_task payload. See hg_core/task_graph/docs/dag_wiring_plan.md section 4.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional


USE_SESSION_RUNNER_ENV = "HG_DAG_USE_SESSION_RUNNER"
SESSION_RUNNER_CMD_ENV = "HG_SESSION_RUNNER_CMD"


def _parse_stdout_for_thread_result(stdout: str) -> Optional[Dict[str, Any]]:
    """Parse stdout for a JSON line with thread_id/thread_url; return dict or None."""
    if not stdout or not isinstance(stdout, str):
        return None
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if "thread_id" not in line and "thread_url" not in line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue
            thread_id = obj.get("thread_id")
            thread_url = obj.get("thread_url")
            if thread_id and not thread_url:
                thread_url = f"https://www.4claw.org/t/{thread_id}"
            if thread_id or thread_url:
                return {"thread_id": thread_id, "thread_url": thread_url}
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def run_via_session_runner(
    task_name: str,
    resolved_inputs: Dict[str, Any],
    memory_profile: Optional[str] = None,
    timeout_s: int = 300,
) -> Dict[str, Any]:
    """
    Run one task via the external session runner (e.g. hg cron run).

    Resolves job_id from task_name via job_registry, runs HG_SESSION_RUNNER_CMD with
    job_id and timeout, passes HG_DAG_INPUTS and optionally HG_OVERRIDE_MESSAGE
    in env. Captures stdout and parses for thread_id/thread_url (fourclaw-style) if present.

    Returns:
        {ok, outputs?, returncode, stdout_tail, error?} – same shape as dispatch_agent.
    """
    use_env = os.environ.get(USE_SESSION_RUNNER_ENV, "").strip().lower() in ("1", "true", "yes")
    if not use_env:
        return {}  # signal: not configured
    cmd_raw = os.environ.get(SESSION_RUNNER_CMD_ENV, "").strip()
    if not cmd_raw:
        return {"ok": False, "error": "HG_SESSION_RUNNER_CMD is empty", "returncode": -1}

    try:
        from hg_core.job_registry import get_job_id
        job_id = get_job_id(task_name)
    except Exception:
        job_id = None
    if not job_id:
        return {"ok": False, "error": f"No job_id for task {task_name}", "returncode": -1}

    # Build command: CMD can be "hg cron run" -> ["hg", "cron", "run", job_id, "--timeout", str(timeout_s*1000)]
    parts = [p.strip() for p in cmd_raw.split() if p.strip()]
    if not parts:
        return {"ok": False, "error": "HG_SESSION_RUNNER_CMD is empty", "returncode": -1}
    cmd = parts + [job_id]
    # Optional: add timeout if runner supports it (e.g. --timeout 300000)
    try:
        cmd.extend(["--timeout", str(timeout_s * 1000)])
    except Exception:
        pass

    env = dict(os.environ)
    env["HG_DAG_INPUTS"] = json.dumps(resolved_inputs)
    if isinstance(memory_profile, str) and memory_profile.strip():
        env["HG_MEMORY_PROFILE"] = memory_profile.strip()
    # Optional: run run_task to get message for HG_OVERRIDE_MESSAGE (skip for simplicity; runner can use DAG inputs)
    # env["HG_OVERRIDE_MESSAGE"] = ...

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "returncode": -1}
    except Exception as e:
        return {"ok": False, "error": str(e), "returncode": -1}

    stdout_str = (result.stdout or "") if result.stdout else ""
    stdout_tail = stdout_str[-2000:] if len(stdout_str) > 2000 else stdout_str
    out: Dict[str, Any] = {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": stdout_tail[-500:] if len(stdout_tail) > 500 else stdout_tail,
    }
    thread_result = _parse_stdout_for_thread_result(stdout_str)
    if thread_result:
        out["outputs"] = thread_result
    if result.returncode != 0 and not out.get("error"):
        out["error"] = (result.stderr or "").strip()[:500] or f"exit code {result.returncode}"
    return out
