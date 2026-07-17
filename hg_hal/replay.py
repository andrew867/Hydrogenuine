"""HAL replay verifier — deterministic state/hash comparison."""

from __future__ import annotations

from hg_hal.event_log import HalEventLogAdapter
from hg_hal.models import HalRuntimeState
from hg_hal.reducer import HalReducer
from hg_hal.state import initial_state


class HalReplayVerifier:
    def __init__(self, *, reducer: HalReducer | None = None) -> None:
        self._reducer = reducer or HalReducer()

    def verify(
        self,
        log: HalEventLogAdapter,
        *,
        expected_state: HalRuntimeState | None = None,
    ) -> tuple[bool, str, HalRuntimeState]:
        events = log.read_all()
        if not events:
            return False, "empty event log", initial_state()
        replayed = self._reducer.fold(events, initial=initial_state())
        if expected_state is not None and replayed.state_hash != expected_state.state_hash:
            return False, "state_hash mismatch on replay", replayed
        seqs = [event.seq for event in events]
        if seqs != sorted(seqs) or len(seqs) != len(set(seqs)):
            return False, "event ordering violation", replayed
        return True, "ok", replayed


def verify_replay(
    log: HalEventLogAdapter,
    *,
    expected_state: HalRuntimeState | None = None,
) -> tuple[bool, str]:
    ok, reason, _ = HalReplayVerifier().verify(log, expected_state=expected_state)
    return ok, reason


__all__ = ["HalReplayVerifier", "verify_replay"]
