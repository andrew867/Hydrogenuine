"""Rollback drill bus event drafts (CT-07 RBK)."""

from __future__ import annotations

from typing import Any


def _draft(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    from hg_runtime.contract import draft

    return draft(event_type, payload, causal_parents=[])


def drill_started(drill_id: str, *, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return _draft("RBK_DRILL_STARTED", {"drill_id": drill_id, **(detail or {})})


def drill_completed(outcome: dict[str, Any]) -> dict[str, Any]:
    return _draft("RBK_DRILL_COMPLETED", outcome)


def drill_failed(drill_id: str, *, reason_code: str) -> dict[str, Any]:
    return _draft("RBK_DRILL_FAILED", {"drill_id": drill_id, "reason_code": reason_code})


def lockdown_entered(*, bundle_id: str, reason_code: str) -> dict[str, Any]:
    return _draft("RBK_LOCKDOWN_ENTERED", {"bundle_id": bundle_id, "reason_code": reason_code})


def compensation_receipted(receipt: dict[str, Any]) -> dict[str, Any]:
    return _draft("RBK_COMPENSATION_RECEIPTED", receipt)


__all__ = [
    "compensation_receipted",
    "drill_completed",
    "drill_failed",
    "drill_started",
    "lockdown_entered",
]
