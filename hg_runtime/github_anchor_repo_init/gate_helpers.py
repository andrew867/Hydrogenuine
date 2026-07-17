"""Gate helpers for GitHub anchor repo init."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PROOFS = WORKSPACE / "docs/proofs/github_anchor_repo_init"
REPORTS = WORKSPACE / "docs/reports/phases"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict]) -> dict:
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


__all__ = ["PROOFS", "REPORTS", "WORKSPACE", "base_report", "now_stamp"]
