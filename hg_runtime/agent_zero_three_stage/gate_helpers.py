"""Gate helpers for Agent Zero three-stage proof."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs/reports/phases"
PROOFS = WORKSPACE / "docs/proofs/agent_zero_three_stage"
STAGE_STATE = WORKSPACE / ".hg-local/agent_zero_three_stage/stage_status.json"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ok": not str(verdict).startswith("RED"),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
