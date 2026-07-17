"""Gateway database hardening checks and invariants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from hg_gateway.db import SCHEMA_VERSION, get_connection


_REQUIRED_INDEXES = {
    "idx_chats_tenant_id",
    "idx_messages_tenant_chat",
    "idx_agents_tenant_chat",
    "idx_approvals_tenant_id",
    "idx_events_tenant_chat",
    "idx_agent_decisions_agent_timestamp",
    "idx_sealed_receipts_tenant_created",
}


@dataclass(frozen=True)
class HardeningCheck:
    check: str
    passed: bool
    details: dict[str, Any]


def _index_names() -> set[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {str(row["name"]) for row in rows}


def _schema_version() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(version) AS version FROM _schema_version").fetchone()
    return int(row["version"] or 0) if row else 0


def _unicode_roundtrip() -> tuple[bool, dict[str, Any]]:
    sample = "naïve 🚀 こんにちは مرحبا"
    with get_connection() as conn:
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS gateway_hardening_probe (value TEXT NOT NULL)")
        conn.execute("DELETE FROM gateway_hardening_probe")
        conn.execute("INSERT INTO gateway_hardening_probe (value) VALUES (?)", (sample,))
        row = conn.execute("SELECT value FROM gateway_hardening_probe").fetchone()
    actual = row["value"] if row else None
    return actual == sample, {"expected": sample, "actual": actual}


def _repeatable_bootstrap() -> bool:
    with get_connection() as conn:
        before = conn.execute("SELECT MAX(version) AS version FROM _schema_version").fetchone()
        before_version = int(before["version"] or 0) if before else 0
    with get_connection() as conn:
        after = conn.execute("SELECT MAX(version) AS version FROM _schema_version").fetchone()
        after_version = int(after["version"] or 0) if after else 0
    return before_version == after_version == SCHEMA_VERSION


def verify_gateway_hardening() -> dict[str, Any]:
    checks: list[HardeningCheck] = []
    checks.append(
        HardeningCheck(
            check="schema_version_current",
            passed=_schema_version() == SCHEMA_VERSION,
            details={"expected": SCHEMA_VERSION, "actual": _schema_version()},
        )
    )
    indexes = _index_names()
    missing_indexes = sorted(_REQUIRED_INDEXES - indexes)
    checks.append(
        HardeningCheck(
            check="required_indexes_present",
            passed=not missing_indexes,
            details={"required": sorted(_REQUIRED_INDEXES), "missing": missing_indexes},
        )
    )
    unicode_ok, unicode_details = _unicode_roundtrip()
    checks.append(HardeningCheck(check="unicode_roundtrip", passed=unicode_ok, details=unicode_details))
    checks.append(
        HardeningCheck(
            check="repeatable_bootstrap",
            passed=_repeatable_bootstrap(),
            details={"expected": SCHEMA_VERSION},
        )
    )
    passed = sum(1 for check in checks if check.passed)
    return {
        "backend": "postgres" if _schema_version() >= SCHEMA_VERSION else "sqlite",
        "checks_total": len(checks),
        "checks_passed": passed,
        "all_passed": passed == len(checks),
        "checks": [check.__dict__ for check in checks],
    }

