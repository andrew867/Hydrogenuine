"""Gate helpers for EXCITON Phase 0 evals."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "exciton"
FIXTURES = WORKSPACE / "tests" / "fixtures" / "exciton"


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
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def scan_forbidden(obj: Any, path: str = "") -> list[str]:
    """Return paths whose key matches a forbidden field fragment (secret-exposure scan)."""
    from hg_runtime.exciton.panel_registry import field_key_is_forbidden

    bad: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if field_key_is_forbidden(str(k)):
                bad.append(path + "/" + str(k))
            bad += scan_forbidden(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += scan_forbidden(v, f"{path}[{i}]")
    return bad


__all__ = ["FIXTURES", "PROOFS", "REPORTS", "WORKSPACE", "base_report", "now_stamp", "scan_forbidden"]
