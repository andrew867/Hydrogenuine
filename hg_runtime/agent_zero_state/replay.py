"""Replay — reconstruct AgentState from turn journal."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_zero_state.reducer import reduce_state
from hg_runtime.agent_zero_state.state import AgentState, create_agent_state
from hg_runtime.agent_zero_state.turn_journal import TurnJournal, TurnJournalError, journal_path_for_run
from hg_runtime.agent_zero_state.turn_receipt import TurnReceipt
from hg_runtime.agent_zero_state.types import TurnReceiptVerdict


def receipt_from_journal_entry(entry: dict) -> TurnReceipt:
    verdict_str = entry.get("verdict", "")
    try:
        verdict = TurnReceiptVerdict(verdict_str)
    except ValueError:
        verdict = TurnReceiptVerdict.RED_TURN_EMPTY
    return TurnReceipt(
        receipt_id=entry["receipt_id"],
        agent_id=entry["agent_id"],
        run_id=entry.get("run_id"),
        turn_index=entry["turn_index"],
        turn_started_at=entry["turn_started_at"],
        turn_finished_at=entry["turn_finished_at"],
        runtime_mode=entry["runtime_mode"],
        observe_snapshot_ref=entry["observe_snapshot_ref"],
        capability_menu_ref=entry["capability_menu_ref"],
        turn_intent_ref=entry.get("turn_intent_ref"),
        chosen_action=entry["chosen_action"],
        action_status=entry["action_status"],
        action_result_ref=entry.get("action_result_ref"),
        provider_receipt_refs=entry.get("provider_receipt_refs", []),
        live_read_receipt_refs=entry.get("live_read_receipt_refs", []),
        witness_receipt_ref=entry.get("witness_receipt_ref"),
        failure_posture_ref=entry.get("failure_posture_ref"),
        scope_request_refs=entry.get("scope_request_refs", []),
        operator_question_refs=entry.get("operator_question_refs", []),
        broker_decision_ref=entry.get("broker_decision_ref"),
        output_quality_ref=entry.get("output_quality_ref"),
        external_side_effect=entry.get("external_side_effect", False),
        published=entry.get("published", False),
        sent=entry.get("sent", False),
        fixture_used=entry.get("fixture_used", False),
        dry_run_used=entry.get("dry_run_used", False),
        proof_replay_used=entry.get("proof_replay_used", False),
        hidden_cot_stored=entry.get("hidden_cot_stored", False),
        secrets_stored=entry.get("secrets_stored", False),
        verdict=verdict,
        hash=entry.get("hash", ""),
        previous_turn_hash=entry.get("previous_turn_hash"),
    )


def replay_agent_state(
    initial_state: AgentState,
    journal: TurnJournal,
) -> AgentState:
    """Replay journal entries to reconstruct final agent state."""
    journal.verify_chain()
    state = initial_state
    for entry in journal.read_all():
        receipt = receipt_from_journal_entry(entry)
        state = reduce_state(state, receipt)
    return state


def replay_from_run(
    run_id: str,
    initial_state: AgentState,
    *,
    base: Path | None = None,
) -> AgentState:
    journal = TurnJournal(journal_path_for_run(run_id, base=base))
    return replay_agent_state(initial_state, journal)


def verify_replay_deterministic(
    initial_state: AgentState,
    journal: TurnJournal,
    expected_state: AgentState,
) -> bool:
    """Return True if replay matches expected state hash."""
    try:
        replayed = replay_agent_state(initial_state, journal)
    except TurnJournalError:
        return False
    return replayed.state_hash == expected_state.state_hash


__all__ = [
    "receipt_from_journal_entry",
    "replay_agent_state",
    "replay_from_run",
    "verify_replay_deterministic",
]
