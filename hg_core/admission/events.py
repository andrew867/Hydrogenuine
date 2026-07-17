"""Admission bus event drafts (CT-06 ADM)."""

from __future__ import annotations

from typing import Any


def _draft(event_type: str, payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    from hg_runtime.contract import draft

    parents = [parent] if parent else []
    return draft(event_type, payload, causal_parents=parents)


def admission_requested(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_ADMISSION_REQUESTED", payload, parent=parent)


def admission_granted(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_ADMISSION_GRANTED", payload, parent=parent)


def admission_refused(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_ADMISSION_REFUSED", payload, parent=parent)


def lock_acquired(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_LOCK_ACQUIRED", payload, parent=parent)


def lock_released(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_LOCK_RELEASED", payload, parent=parent)


def preemption_receipted(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_PREEMPTION_RECEIPTED", payload, parent=parent)


def panic_asserted(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_PANIC_ASSERTED", payload, parent=parent)


def queue_drained(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_QUEUE_DRAINED", payload, parent=parent)


def idempotency_hit(payload: dict[str, Any], *, parent: str | None = None) -> dict[str, Any]:
    return _draft("ADM_IDEMPOTENCY_HIT", payload, parent=parent)


__all__ = [
    "admission_granted",
    "admission_refused",
    "admission_requested",
    "idempotency_hit",
    "lock_acquired",
    "lock_released",
    "panic_asserted",
    "preemption_receipted",
    "queue_drained",
]
