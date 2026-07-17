"""SOAR event reducer — fold events into runtime state."""

from __future__ import annotations

from hg_soar.events import SOAR_DECISION_RECORDED, SOAR_FAILED_CLOSED, SOAR_REQUEST_RECEIVED
from hg_soar.models import SoarEvent, SoarRuntimeState
from hg_soar.state import compute_state_hash, initial_state
from hg_soar.types import D7Binding


class SoarReducer:
    """Deterministic fold over SOAR events."""

    def reduce(self, state: SoarRuntimeState, event: SoarEvent) -> SoarRuntimeState:
        processed = set(state.processed_idempotency_keys)
        last_decision = state.last_decision_id
        last_binding = state.last_binding

        if event.event_type == SOAR_REQUEST_RECEIVED:
            key = str(event.payload.get("idempotency_key", ""))
            if key:
                processed.add(key)
        elif event.event_type in {SOAR_DECISION_RECORDED, SOAR_FAILED_CLOSED}:
            last_decision = str(event.payload.get("decision_id", last_decision))
            binding_raw = event.payload.get("binding")
            if binding_raw in {"ACCEPT", "DEFER", "REJECT", "NO_OP"}:
                last_binding = binding_raw

        seq = event.seq
        event_count = state.event_count + 1
        state_hash = compute_state_hash(
            seq=seq,
            processed_idempotency_keys=frozenset(processed),
            last_decision_id=last_decision,
            event_count=event_count,
            last_binding=last_binding,
        )
        return SoarRuntimeState(
            seq=seq,
            state_hash=state_hash,
            processed_idempotency_keys=frozenset(processed),
            last_decision_id=last_decision,
            event_count=event_count,
            last_binding=last_binding,
        )

    def fold(self, events: list[SoarEvent], *, initial: SoarRuntimeState | None = None) -> SoarRuntimeState:
        state = initial or initial_state()
        for event in sorted(events, key=lambda e: e.seq):
            state = self.reduce(state, event)
        return state


__all__ = ["SoarReducer"]
