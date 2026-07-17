"""SOAR replay verifier — deterministic state/hash comparison."""

from __future__ import annotations

from hg_soar.event_log import SoarEventLogAdapter
from hg_soar.models import SoarRuntimeState
from hg_soar.reducer import SoarReducer
from hg_soar.state import initial_state


class SoarReplayVerifier:
    def __init__(self, *, reducer: SoarReducer | None = None) -> None:
        self._reducer = reducer or SoarReducer()

    def verify(
        self,
        log: SoarEventLogAdapter,
        *,
        expected_state: SoarRuntimeState | None = None,
    ) -> tuple[bool, str, SoarRuntimeState]:
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
    log: SoarEventLogAdapter,
    *,
    expected_state: SoarRuntimeState | None = None,
) -> tuple[bool, str]:
    ok, reason, _ = SoarReplayVerifier().verify(log, expected_state=expected_state)
    return ok, reason


__all__ = ["SoarReplayVerifier", "verify_replay"]
