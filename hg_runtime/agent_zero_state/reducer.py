"""TurnStateReducer — apply turn receipt to agent state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.state import AgentState, validate_agent_state
from hg_runtime.agent_zero_state.turn_journal import TurnJournal, TurnJournalError, state_path_for_run
from hg_runtime.agent_zero_state.turn_receipt import TurnReceipt, validate_turn_receipt
from hg_runtime.agent_zero_state.types import TurnReceiptVerdict


def reduce_state(state: AgentState, receipt: TurnReceipt) -> AgentState:
    """Apply validated turn receipt to produce next agent state."""
    verdict, validated_receipt = validate_turn_receipt(receipt)
    if verdict.value.startswith("RED_"):
        raise TurnJournalError(f"cannot reduce with invalid receipt: {verdict.value}")

    provider_refs = list(state.provider_status_refs)
    for ref in validated_receipt.provider_receipt_refs:
        if ref and ref not in provider_refs:
            provider_refs.append(ref)

    live_refs = list(state.live_read_status_refs)
    for ref in validated_receipt.live_read_receipt_refs:
        if ref and ref not in live_refs:
            live_refs.append(ref)

    scope_refs = list(state.scope_request_refs)
    for ref in validated_receipt.scope_request_refs:
        if ref and ref not in scope_refs:
            scope_refs.append(ref)

    failure_refs = list(state.failure_posture_refs)
    if validated_receipt.failure_posture_ref:
        failure_refs.append(validated_receipt.failure_posture_ref)

    next_state = AgentState(
        agent_id=state.agent_id,
        run_id=state.run_id or validated_receipt.run_id,
        runtime_mode=validated_receipt.runtime_mode,
        created_at=state.created_at,
        updated_at=validated_receipt.turn_finished_at,
        turn_index=validated_receipt.turn_index,
        last_turn_receipt_ref=validated_receipt.receipt_id,
        last_turn_hash=validated_receipt.hash,
        operator_presence_state=state.operator_presence_state,
        provider_status_refs=provider_refs,
        live_read_status_refs=live_refs,
        witness_state_ref=validated_receipt.witness_receipt_ref or state.witness_state_ref,
        failure_posture_refs=failure_refs,
        scope_request_refs=scope_refs,
        open_thread_refs=list(state.open_thread_refs),
        memory_refs=list(state.memory_refs),
        capability_menu_ref=validated_receipt.capability_menu_ref,
        budget_state=dict(state.budget_state),
        stop_panic_state=dict(state.stop_panic_state),
        dirty_reason=None,
    ).with_hash()

    sv, _ = validate_agent_state(next_state)
    if sv.value.startswith("RED_"):
        raise TurnJournalError(f"reduced state invalid: {sv.value}")
    return next_state


def persist_agent_state(state: AgentState, run_id: str, *, base: Path | None = None) -> Path:
    path = state_path_for_run(run_id, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state.to_payload(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def load_agent_state(run_id: str, *, base: Path | None = None) -> AgentState | None:
    path = state_path_for_run(run_id, base=base)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentState(
        agent_id=data["agent_id"],
        run_id=data.get("run_id"),
        runtime_mode=data["runtime_mode"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        turn_index=data.get("turn_index", 0),
        last_turn_receipt_ref=data.get("last_turn_receipt_ref"),
        last_turn_hash=data.get("last_turn_hash"),
        state_hash=data.get("state_hash", ""),
        operator_presence_state=data.get("operator_presence_state", "operator_unknown"),
        provider_status_refs=data.get("provider_status_refs", []),
        live_read_status_refs=data.get("live_read_status_refs", []),
        witness_state_ref=data.get("witness_state_ref"),
        failure_posture_refs=data.get("failure_posture_refs", []),
        scope_request_refs=data.get("scope_request_refs", []),
        open_thread_refs=data.get("open_thread_refs", []),
        memory_refs=data.get("memory_refs", []),
        capability_menu_ref=data.get("capability_menu_ref"),
        budget_state=data.get("budget_state", {}),
        stop_panic_state=data.get("stop_panic_state", {}),
        dirty_reason=data.get("dirty_reason"),
    )


def apply_turn(
    state: AgentState,
    receipt: TurnReceipt,
    journal: TurnJournal,
    *,
    persist_run_id: str | None = None,
    base: Path | None = None,
) -> AgentState:
    """Reduce, append journal, optionally persist."""
    next_state = reduce_state(state, receipt)
    journal.append(receipt)
    journal.verify_chain()
    if persist_run_id:
        persist_agent_state(next_state, persist_run_id, base=base)
    return next_state


__all__ = [
    "apply_turn",
    "load_agent_state",
    "persist_agent_state",
    "reduce_state",
]
