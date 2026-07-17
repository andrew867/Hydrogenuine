"""Shared helpers for model provider fabric gates."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
FABRIC_CONFIG = WORKSPACE / "configs" / "model_providers" / "model_provider_fabric.example.json"
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "model_provider_fabric"

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


def run_gate_script(relative: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, relative],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"ok": result.returncode == 0, "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}
    payload["exit_code"] = result.returncode
    return payload


def config_has_no_secrets(path: Path) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            return False, "secret-like pattern in config"
    return True, "ok"


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ok": verdict not in {"RED_AUTHORITY_CONVERSION", "RED_PROVIDER_UNSAFE", "RED_LOOP_UNBOUNDED", "RED_GATE_FAILURE"},
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
