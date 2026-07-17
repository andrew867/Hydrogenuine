"""Turn replay tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.reducer import apply_turn, reduce_state  # noqa: E402
from hg_runtime.agent_zero_state.replay import replay_agent_state, verify_replay_deterministic  # noqa: E402
from hg_runtime.agent_zero_state.state import create_agent_state  # noqa: E402
from hg_runtime.agent_zero_state.turn_journal import TurnJournal  # noqa: E402
from hg_runtime.agent_zero_state.turn_receipt import build_turn_receipt  # noqa: E402


def test_reducer_deterministic():
    _, initial = create_agent_state(agent_id="agent-r", runtime_mode="local_dev", run_id="run-r")
    _, r1 = build_turn_receipt(
        agent_id="agent-r",
        turn_index=1,
        runtime_mode="local_dev",
        observe_snapshot_ref="snap-1",
        capability_menu_ref="menu-1",
        chosen_action="rest_turn",
        provider_receipt_refs=["prov-1"],
        live_read_receipt_refs=["live-1"],
    )
    s_a = reduce_state(initial, r1)
    s_b = reduce_state(initial, r1)
    assert s_a.state_hash == s_b.state_hash


def test_journal_replay_reconstructs_same_state(tmp_path: Path):
    _, initial = create_agent_state(agent_id="agent-r", runtime_mode="local_dev", run_id="run-r")
    journal = TurnJournal(tmp_path / "turn_journal.jsonl")
    _, r1 = build_turn_receipt(
        agent_id="agent-r",
        turn_index=1,
        runtime_mode="local_dev",
        observe_snapshot_ref="snap-1",
        capability_menu_ref="menu-1",
        chosen_action="witness_turn",
        provider_receipt_refs=["prov-1"],
        live_read_receipt_refs=["live-1"],
    )
    final = apply_turn(initial, r1, journal)
    replayed = replay_agent_state(initial, journal)
    assert verify_replay_deterministic(initial, journal, final)
    assert replayed.state_hash == final.state_hash
    assert replayed.turn_index == 1
    assert replayed.last_turn_receipt_ref == r1.receipt_id
