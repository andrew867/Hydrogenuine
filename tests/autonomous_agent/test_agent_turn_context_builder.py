"""Context builder tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict
from hg_runtime.agent_turn_engine.context_builder import build_observe_snapshot_for_turn, load_or_initialize_agent_state
from hg_runtime.agent_turn_engine.errors import AgentTurnValidationError
from hg_runtime.agent_turn_engine.schema import build_agent_turn_request

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")

def test_provider_unavailable_yellow():
    req = build_agent_turn_request(agent_id="ctx-a", run_id="ctx-run-1", allow_provider=False)
    state = load_or_initialize_agent_state(req)
    v, snap = build_observe_snapshot_for_turn(request=req, agent_state=state, turn_index=1)
    assert v == ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE
    assert not snap.provider_reality_refs

def test_live_read_unavailable_yellow():
    req = build_agent_turn_request(agent_id="ctx-b", run_id="ctx-run-2", allow_live_read=False)
    state = load_or_initialize_agent_state(req)
    v, snap = build_observe_snapshot_for_turn(request=req, agent_state=state, turn_index=1)
    assert v in (ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE, ObserveSnapshotVerdict.YELLOW_LIVE_READ_UNAVAILABLE)

def test_fixture_rejected():
    req = build_agent_turn_request(agent_id="ctx-c", run_id="ctx-run-3", runtime_mode="fixture")
    with pytest.raises(AgentTurnValidationError):
        load_or_initialize_agent_state(req)
