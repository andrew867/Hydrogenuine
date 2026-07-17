"""Phase 39 boundary monitor.

Captures and hashes the hard-boundary state of the soak and detects any attempt
to drift it. The six boundary flags must remain false for the entire run; if a
task attempts to flip one, the monitor reports drift so the loop can reject it
without ever honoring the attempt.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    BOUNDARY_SNAPSHOT_SCHEMA,
    PHASE19_STATUS,
    PHASE24_STATUS,
    neutral_boundary_flags,
)


def boundary_state_hash(state: Mapping[str, Any]) -> str:
    desc = {field: bool(state.get(field, False)) for field in BOUNDARY_FLAG_FIELDS}
    desc["phase19_status"] = state.get("phase19_status", PHASE19_STATUS)
    desc["phase24_status"] = state.get("phase24_status", PHASE24_STATUS)
    return canonical_hash(desc)


def boundary_snapshot(state: Mapping[str, Any], *, iteration: int = -1) -> dict[str, Any]:
    flags = {field: bool(state.get(field, False)) for field in BOUNDARY_FLAG_FIELDS}
    snapshot = {
        "schema": BOUNDARY_SNAPSHOT_SCHEMA,
        "iteration": iteration,
        **flags,
        "phase19_status": state.get("phase19_status", PHASE19_STATUS),
        "phase24_status": state.get("phase24_status", PHASE24_STATUS),
        "all_boundaries_false": not any(flags.values()),
        "boundary_state_hash": boundary_state_hash(state),
    }
    return snapshot


def detect_boundary_drift(attempted_effect: Mapping[str, Any]) -> list[str]:
    """Return the boundary fields a task attempted to flip true (empty if none)."""
    return [field for field in BOUNDARY_FLAG_FIELDS if attempted_effect.get(field)]


def neutral_boundary_state() -> dict[str, Any]:
    return {
        **neutral_boundary_flags(),
        "phase19_status": PHASE19_STATUS,
        "phase24_status": PHASE24_STATUS,
    }


__all__ = [
    "boundary_state_hash",
    "boundary_snapshot",
    "detect_boundary_drift",
    "neutral_boundary_state",
]
