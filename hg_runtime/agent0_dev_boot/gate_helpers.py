"""Shared helpers for Agent #0 dev boot prep gates."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "agent0_dev_boot_prep"
COMPOSE = WORKSPACE / "docker-compose.yml"

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
)


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


def compose_has_hg_db_wait() -> tuple[bool, str]:
    if not COMPOSE.is_file():
        return False, "docker-compose.yml missing"
    text = COMPOSE.read_text(encoding="utf-8")
    if "hg-proof:" not in text or "hg-db:" not in text:
        return False, "hg-proof or hg-db missing"
    if "depends_on:" not in text or "service_healthy" not in text:
        return False, "hg-proof missing depends_on service_healthy"
    return True, "hg-proof waits for hg-db healthy"


def gitignore_has_local_runtime() -> tuple[bool, str]:
    gi = WORKSPACE / ".gitignore"
    if not gi.is_file():
        return False, ".gitignore missing"
    text = gi.read_text(encoding="utf-8")
    if ".hg-local/" not in text:
        return False, ".hg-local/ not gitignored"
    return True, "ok"
