"""HAL event reducer — fold events into runtime state."""

from __future__ import annotations

from hg_hal.events import (
    HAL_DEGRADED_MODE_ENTERED,
    HAL_PANIC_ENTERED,
    HAL_REPLAY_VERIFIED,
    HAL_REQUEST_RECEIVED,
)
from hg_hal.models import HalDegradedMode, HalEvent, HalPanicState, HalRuntimeState
from hg_hal.state import compute_state_hash, initial_state


class HalReducer:
    """Deterministic fold over HAL events."""

    def reduce(self, state: HalRuntimeState, event: HalEvent) -> HalRuntimeState:
        panic = state.panic
        degraded = state.degraded
        processed = set(state.processed_idempotency_keys)
        last_decision = state.last_decision_id

        if event.event_type == HAL_PANIC_ENTERED:
            panic = HalPanicState(
                active=True,
                entered_at=event.timestamp,
                reason_code=str(event.payload.get("reason_code", "panic")),
            )
        elif event.event_type == HAL_DEGRADED_MODE_ENTERED:
            degraded = HalDegradedMode(
                active=True,
                mode=str(event.payload.get("mode", "operator_only")),
                entered_at=event.timestamp,
            )
        elif event.event_type == HAL_REQUEST_RECEIVED:
            key = str(event.payload.get("idempotency_key", ""))
            if key:
                processed.add(key)
        elif event.event_type in {
            "HAL_DECISION_PROPOSED",
            "HAL_FAILED_CLOSED",
            "HAL_REJECTED",
        }:
            last_decision = str(event.payload.get("decision_id", last_decision))

        seq = event.seq
        event_count = state.event_count + 1
        state_hash = compute_state_hash(
            seq=seq,
            panic=panic,
            degraded=degraded,
            processed_idempotency_keys=frozenset(processed),
            last_decision_id=last_decision,
            event_count=event_count,
        )
        return HalRuntimeState(
            seq=seq,
            state_hash=state_hash,
            panic=panic,
            degraded=degraded,
            processed_idempotency_keys=frozenset(processed),
            last_decision_id=last_decision,
            event_count=event_count,
        )

    def fold(self, events: list[HalEvent], *, initial: HalRuntimeState | None = None) -> HalRuntimeState:
        state = initial or initial_state()
        for event in sorted(events, key=lambda e: e.seq):
            state = self.reduce(state, event)
        return state


__all__ = ["HalReducer"]
