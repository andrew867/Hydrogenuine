"""Agent turn engine integration tests."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request

VALID_OUTPUT = json.dumps({
    "observation_summary": "Quiet.",
    "reasoning_summary": "Resting.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")

def test_provider_unavailable_honest_yellow(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(tmp_path))
    req = build_agent_turn_request(agent_id="eng-a", run_id="eng-run-1", allow_provider=False)
    out = run_single_agent_turn(req, base=tmp_path)
    assert isinstance(out, AgentTurnResult)
    assert out.verdict in (
        AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE,
        AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED,
    )
    assert out.broker_decision_ref
    assert out.turn_receipt_ref
    assert out.reasoning_failure_ref

def test_full_turn_with_provider_double(tmp_path):
    req = build_agent_turn_request(agent_id="eng-b", run_id="eng-run-2", allow_provider=True)
    _, snap_menu_observe = __import__("hg_runtime.agent_zero_state.observe_snapshot", fromlist=["build_observe_snapshot"]).build_observe_snapshot(
        agent_id="eng-b", turn_index=1, runtime_mode="local_dev",
        provider_reality_refs=["prov-test"], live_read_receipt_refs=["live-test"])
    def _invoke(_p, _r):
        return VALID_OUTPUT
    out = run_single_agent_turn(req, provider_invoke=_invoke, base=tmp_path)
    assert isinstance(out, AgentTurnResult)
    assert out.observe_snapshot_ref
    assert out.capability_menu_ref
    assert out.broker_decision_ref
    assert out.turn_receipt_ref
    assert out.journal_ref
    assert out.dispatch_result_ref

def test_no_broker_bypass(tmp_path):
    req = build_agent_turn_request(agent_id="eng-c", run_id="eng-run-3")
    out = run_single_agent_turn(req, base=tmp_path)
    assert isinstance(out, (AgentTurnResult, AgentTurnFailure))
    if isinstance(out, AgentTurnResult):
        assert out.broker_decision_ref
