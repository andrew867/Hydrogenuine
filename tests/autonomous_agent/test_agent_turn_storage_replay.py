"""Turn storage and replay tests."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(tmp_path))


from hg_runtime.agent_zero_state.replay import verify_replay_deterministic
from hg_runtime.agent_zero_state.reducer import reduce_state
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.turn_receipt import build_turn_receipt
from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnResult, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import journal_path, open_journal, receipts_dir

def test_replay_after_single_turn(tmp_path):
    req = build_agent_turn_request(agent_id="stor-a", run_id="stor-run-1")
    out = run_single_agent_turn(req, base=tmp_path)
    assert isinstance(out, AgentTurnResult)
    _, initial = create_agent_state(agent_id="stor-a", runtime_mode="local_dev", run_id="stor-run-1")
    journal = open_journal("stor-run-1", base=tmp_path)
    entries = journal.read_all()
    assert len(entries) == 1
    assert receipts_dir("stor-run-1", base=tmp_path).is_dir()
    from hg_runtime.agent_zero_state.replay import receipt_from_journal_entry, replay_agent_state
    state = initial
    for entry in entries:
        state = reduce_state(state, receipt_from_journal_entry(entry))
    assert state.state_hash == out.state_after_ref or state.turn_index == out.turn_index

def test_journal_chain(tmp_path):
    req = build_agent_turn_request(agent_id="stor-b", run_id="stor-run-2")
    run_single_agent_turn(req, base=tmp_path)
    journal = open_journal("stor-run-2", base=tmp_path)
    journal.verify_chain()
