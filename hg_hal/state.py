"""HAL runtime state helpers."""

from __future__ import annotations

from hg_core.governance.canonical_hash import canonical_hash

from hg_hal.models import HalDegradedMode, HalPanicState, HalRuntimeState


def initial_state() -> HalRuntimeState:
    panic = HalPanicState()
    degraded = HalDegradedMode()
    body = {
        "seq": 0,
        "panic": panic.to_payload(),
        "degraded": degraded.to_payload(),
        "processed_idempotency_keys": [],
        "last_decision_id": None,
        "event_count": 0,
    }
    return HalRuntimeState(
        seq=0,
        state_hash=canonical_hash(body),
        panic=panic,
        degraded=degraded,
        processed_idempotency_keys=frozenset(),
        last_decision_id=None,
        event_count=0,
    )


def compute_state_hash(
    *,
    seq: int,
    panic: HalPanicState,
    degraded: HalDegradedMode,
    processed_idempotency_keys: frozenset[str],
    last_decision_id: str | None,
    event_count: int,
) -> str:
    body = {
        "seq": seq,
        "panic": panic.to_payload(),
        "degraded": degraded.to_payload(),
        "processed_idempotency_keys": sorted(processed_idempotency_keys),
        "last_decision_id": last_decision_id,
        "event_count": event_count,
    }
    return canonical_hash(body)


__all__ = ["compute_state_hash", "initial_state"]
