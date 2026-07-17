"""SOAR runtime state helpers."""

from __future__ import annotations

from hg_core.governance.canonical_hash import canonical_hash

from hg_soar.models import SoarRuntimeState
from hg_soar.types import D7Binding


def initial_state() -> SoarRuntimeState:
    body = {
        "seq": 0,
        "processed_idempotency_keys": [],
        "last_decision_id": None,
        "event_count": 0,
        "last_binding": None,
    }
    return SoarRuntimeState(
        seq=0,
        state_hash=canonical_hash(body),
        processed_idempotency_keys=frozenset(),
        last_decision_id=None,
        event_count=0,
        last_binding=None,
    )


def compute_state_hash(
    *,
    seq: int,
    processed_idempotency_keys: frozenset[str],
    last_decision_id: str | None,
    event_count: int,
    last_binding: D7Binding | None,
) -> str:
    body = {
        "seq": seq,
        "processed_idempotency_keys": sorted(processed_idempotency_keys),
        "last_decision_id": last_decision_id,
        "event_count": event_count,
        "last_binding": last_binding,
    }
    return canonical_hash(body)


__all__ = ["compute_state_hash", "initial_state"]
