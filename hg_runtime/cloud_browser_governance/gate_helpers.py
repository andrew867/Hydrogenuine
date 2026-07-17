"""Cloud browser governance gate helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "cloud_browser_tool_governance"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_report(name: str, body: str) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / name
    path.write_text(body, encoding="utf-8")
    return path


def run_script(relative: str, timeout: int = 300) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, relative],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"ok": result.returncode == 0}
    payload["exit_code"] = result.returncode
    return payload


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ok": not verdict.startswith("RED"),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["PROOFS", "WORKSPACE", "base_report", "now_stamp", "run_script", "write_report"]
