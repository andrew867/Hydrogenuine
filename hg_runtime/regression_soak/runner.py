"""Regression soak runner — bounded iteration/duration execution engine."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.regression_soak.schemas import (
    COMMAND_GROUPS,
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    DEFAULT_DURATION_MINUTES,
    DEFAULT_ITERATION_COUNT,
    OPTIONAL_GATE_COMMANDS,
    validate_command,
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_command(cmd: str, cwd: Path, timeout: int) -> dict:
    ok, reason = validate_command(cmd)
    if not ok:
        return {
            "command": cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": reason,
            "duration_seconds": 0.0,
            "passed": False,
            "rejected": True,
            "rejection_reason": reason,
            "timestamp": _stamp(),
        }
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd.split(),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        return {
            "command": cmd,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
            "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
            "duration_seconds": round(elapsed, 2),
            "passed": result.returncode == 0,
            "rejected": False,
            "timestamp": _stamp(),
        }
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return {
            "command": cmd,
            "exit_code": -2,
            "stdout": "",
            "stderr": f"TIMEOUT after {timeout}s",
            "duration_seconds": round(elapsed, 2),
            "passed": False,
            "rejected": False,
            "timed_out": True,
            "timestamp": _stamp(),
        }


def _check_dirty_tree(cwd: Path) -> dict:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    files = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    return {
        "dirty": len(files) > 0,
        "files": files,
        "timestamp": _stamp(),
    }


def run_soak(
    repo_root: Path,
    *,
    max_iterations: int = DEFAULT_ITERATION_COUNT,
    max_duration_minutes: float = DEFAULT_DURATION_MINUTES,
    command_timeout: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    groups: list[str] | None = None,
    clock: Any = None,
) -> dict:
    if groups is None:
        groups = list(COMMAND_GROUPS.keys())

    raw_commands = []
    for g in groups:
        raw_commands.extend(COMMAND_GROUPS.get(g, []))

    commands = []
    optional_missing = []
    for cmd in raw_commands:
        if cmd in OPTIONAL_GATE_COMMANDS:
            script_path = cmd.split()[-1]
            if not (repo_root / script_path).exists():
                info = OPTIONAL_GATE_COMMANDS[cmd]
                optional_missing.append({
                    "command": cmd,
                    "reason": info["reason"],
                    "substitute": info["substitute"],
                    "status": "SKIPPED_KNOWN_ABSENT",
                })
                commands.append(info["substitute"])
                continue
        commands.append(cmd)

    if clock is None:
        clock = time

    start_time = clock.monotonic()
    deadline = start_time + max_duration_minutes * 60

    iterations = []
    all_results = []
    dirty_checks = []

    for iteration_idx in range(max_iterations):
        if clock.monotonic() >= deadline:
            break

        iter_results = []
        for cmd in commands:
            if clock.monotonic() >= deadline:
                break
            result = _run_command(cmd, repo_root, command_timeout)
            result["iteration"] = iteration_idx + 1
            iter_results.append(result)
            all_results.append(result)

        dirty = _check_dirty_tree(repo_root)
        dirty["iteration"] = iteration_idx + 1
        dirty_checks.append(dirty)

        if dirty["dirty"]:
            from hg_runtime.regression_soak.schemas import is_known_churn
            unknown_files = [f for f in dirty["files"] if not is_known_churn(f.lstrip("?! MAD "))]
            if unknown_files:
                dirty["has_unknown_churn"] = True
                dirty["unknown_files"] = unknown_files
            else:
                dirty["has_unknown_churn"] = False
            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=repo_root,
                capture_output=True,
                timeout=30,
            )

        iterations.append({
            "iteration": iteration_idx + 1,
            "command_count": len(iter_results),
            "passed": all(r["passed"] for r in iter_results if not r.get("rejected")),
            "results": iter_results,
            "dirty_tree": dirty,
        })

    elapsed = clock.monotonic() - start_time
    return {
        "iterations": iterations,
        "all_results": all_results,
        "dirty_checks": dirty_checks,
        "total_iterations": len(iterations),
        "total_commands": len(all_results),
        "elapsed_seconds": round(elapsed, 2),
        "optional_missing": optional_missing,
    }
