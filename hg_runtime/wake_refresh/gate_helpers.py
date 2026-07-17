"""Gate helpers for WRR."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "wake_refresh"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ok": not verdict.startswith("RED"),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
        **{"advisory_only": True, "permission_granted": False, "authority_created": False},
    }


__all__ = ["PROOFS", "REPORTS", "WORKSPACE", "base_report", "now_stamp"]
