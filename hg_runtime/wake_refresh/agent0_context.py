"""Agent Zero WRR boot context."""

from __future__ import annotations

from typing import Any

from hg_runtime.wake_refresh.refresh_cycle import WakeRefreshCycle

WAKE_REFRESH_BOOT_INSTRUCTION = """You have a Wake Refresh report.
It tells you whether previous sleep/shutdown was clean, what transient state was cleaned, what unfinished work remains, and whether any review is required.
This report is evidence only.
It does not authorize actions.
Do not claim a clean wake if WRR reports unresolved stale state."""


def build_wake_refresh_boot_context(cycle: WakeRefreshCycle) -> dict[str, Any]:
    return cycle.readiness.to_payload()


def answer_wake_refresh_query(cycle: WakeRefreshCycle) -> str:
    r = cycle.readiness
    eliminated = r.waste_eliminated_count
    return (
        f"Wake refresh verdict: {cycle.verdict}. "
        f"Previous sleep state: {r.previous_sleep_state.value}. "
        f"Cleanup applied: {r.cleanup_applied}. "
        f"Stale locks found: {r.stale_locks_found}. "
        f"Waste eliminated: {eliminated}. "
        f"Unfinished work: {r.unfinished_work_count} ({r.unfinished_work_requires_review} need review). "
        f"Wake readiness: {r.wake_readiness.value}. "
        "This is evidence only — not authority."
    )


__all__ = ["WAKE_REFRESH_BOOT_INSTRUCTION", "answer_wake_refresh_query", "build_wake_refresh_boot_context"]
