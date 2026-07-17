"""Build observe context and load agent state for a single turn."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot, build_observe_snapshot, validate_observe_snapshot
from hg_runtime.agent_zero_state.reducer import load_agent_state
from hg_runtime.agent_zero_state.state import AgentState, create_agent_state
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict
from hg_runtime.agent_turn_engine.errors import AgentTurnValidationError
from hg_runtime.agent_turn_engine.schema import AgentTurnRequest, AgentTurnVerdict, load_agent_turn_engine_policy
from hg_runtime.agent_turn_engine.turn_storage import turns_root


def load_or_initialize_agent_state(
    request: AgentTurnRequest,
    *,
    base: Path | None = None,
) -> AgentState:
    """Load persisted state or create a new one for the run."""
    policy = load_agent_turn_engine_policy()
    if request.runtime_mode == "fixture" and not policy.get("fixture_runtime_truth_allowed", False):
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME.value)

    existing = load_agent_state(request.run_id, base=base or turns_root())
    if existing is not None:
        return existing

    verdict, state = create_agent_state(
        agent_id=request.agent_id,
        runtime_mode=request.runtime_mode,
        run_id=request.run_id,
        operator_presence_state=request.operator_presence,
    )
    if verdict.value.startswith("RED_"):
        raise AgentTurnValidationError(verdict.value)
    return state


def _collect_provider_refs(*, allow_provider: bool, runtime_mode: str) -> list[str]:
    if not allow_provider:
        return []
    try:
        from hg_runtime.model_provider_fabric.provider_reality import probe_provider_reality

        probe = probe_provider_reality(runtime_mode=runtime_mode, role="AGENT_TURN_DECISION")
        if probe and getattr(probe, "receipt_id", None):
            return [probe.receipt_id]
        if isinstance(probe, dict) and probe.get("receipt_id"):
            return [str(probe["receipt_id"])]
    except Exception:
        return []
    return []


def _collect_live_read_refs(*, allow_live_read: bool) -> tuple[list[str], str | None, str]:
    if not allow_live_read:
        return [], None, "unknown"
    try:
        from hg_runtime.live_read_endurance.read_endurance_runner import collect_for_observe_snapshot

        refs, cred, freshness = collect_for_observe_snapshot()
        return refs, cred, freshness
    except Exception:
        return [], "credentials_missing", "unavailable"


def build_observe_snapshot_for_turn(
    *,
    request: AgentTurnRequest,
    agent_state: AgentState,
    turn_index: int,
) -> tuple[ObserveSnapshotVerdict, ObserveSnapshot]:
    """Build honest observe snapshot for one turn."""
    policy = load_agent_turn_engine_policy()
    if request.runtime_mode == "fixture" and not policy.get("fixture_runtime_truth_allowed", False):
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME.value)

    provider_refs = _collect_provider_refs(
        allow_provider=request.allow_provider,
        runtime_mode=request.runtime_mode,
    )
    live_refs, _cred, freshness = _collect_live_read_refs(allow_live_read=request.allow_live_read)

    verdict, snapshot = build_observe_snapshot(
        agent_id=agent_state.agent_id,
        turn_index=turn_index,
        runtime_mode=request.runtime_mode,
        operator_presence=request.operator_presence,
        provider_reality_refs=provider_refs,
        live_read_receipt_refs=live_refs,
        freshness_verdict=freshness,
        run_id=request.run_id,
    )

    if verdict == ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS:
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_EMPTY.value)
    if verdict == ObserveSnapshotVerdict.RED_OBSERVE_FIXTURE_RUNTIME:
        raise AgentTurnValidationError(AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME.value)

    _, validated = validate_observe_snapshot(snapshot)
    if policy.get("empty_observe_snapshot_counts_as_success") is False:
        if not validated.provider_reality_refs and not validated.live_read_receipt_refs:
            if verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY:
                verdict = ObserveSnapshotVerdict.YELLOW_NO_ITEMS_AVAILABLE

    return verdict, validated


def observe_context_summary(verdict: ObserveSnapshotVerdict, snapshot: ObserveSnapshot) -> str:
    parts = [f"observe_verdict={verdict.value}"]
    if snapshot.provider_reality_refs:
        parts.append(f"provider_refs={len(snapshot.provider_reality_refs)}")
    if snapshot.live_read_receipt_refs:
        parts.append(f"live_read_refs={len(snapshot.live_read_receipt_refs)}")
    return "; ".join(parts)


def persist_observe_snapshot(snapshot: ObserveSnapshot, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


__all__ = [
    "build_observe_snapshot_for_turn",
    "load_or_initialize_agent_state",
    "observe_context_summary",
    "persist_observe_snapshot",
]
