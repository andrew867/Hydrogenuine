"""Agent turn content dispatch integration tests."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent
from hg_runtime.capability_broker.schema import BrokerDecision, BrokerDecisionStatus, BrokerVerdict
from hg_runtime.agent_turn_engine.errors import AgentTurnDispatchError
from hg_runtime.agent_turn_engine.internal_dispatch import InternalDispatchVerdict, dispatch_internal_action
from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import build_agent_turn_request

VALID_DRAFT = "A thoughtful draft about system design patterns for operator review."

def _menu():
    return build_capability_menu(runtime_mode="local_dev", provider_available=True, live_read_available=True)

def _intent(action, body):
    _, intent = build_turn_intent(agent_id="c-a", turn_index=1, chosen_action=action, menu=_menu(),
        observation_summary="obs", provider_receipt_ref="prov-1", action_params={"body": body})
    return intent

def _decision(action):
    return BrokerDecision(decision_id="dec-c", request_id="req-c", agent_id="c-a", run_id="run-c",
        turn_index=1, chosen_action=action, status=BrokerDecisionStatus.ADMIT_INTERNAL, admitted=True,
        refused=False, deferred=False, internal_only=True, external_side_effect=False, refusal_reasons=[],
        requirements_checked={}, policy_refs=[], created_at="2026-06-17T00:00:00+00:00",
        verdict=BrokerVerdict.GREEN_BROKER_ADMITTED_INTERNAL).with_hash()

def test_synthesize_notes_creates_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    r = dispatch_internal_action(run_id="run-c", turn_index=1, decision=_decision("synthesize_notes"),
        turn_intent=_intent("synthesize_notes", VALID_DRAFT), observe_snapshot_ref="snap-c",
        capability_menu_ref="menu-c", reasoning_receipt_ref="reason-c", base=tmp_path)
    assert r.output_artifact_ref and r.quality_receipt_ref

def test_propose_draft_creates_review_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    r = dispatch_internal_action(run_id="run-c", turn_index=1, decision=_decision("propose_draft"),
        turn_intent=_intent("propose_draft", VALID_DRAFT), observe_snapshot_ref="snap-c",
        capability_menu_ref="menu-c", base=tmp_path)
    assert r.review_candidate_ref

def test_continue_prior_thread(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    intent = _intent("continue_prior_thread", VALID_DRAFT)
    intent = type(intent)(**{**intent.__dict__, "action_params": {"body": VALID_DRAFT, "thread_ref": "thread-9"}})
    r = dispatch_internal_action(run_id="run-c", turn_index=1, decision=_decision("continue_prior_thread"),
        turn_intent=intent, observe_snapshot_ref="snap-c", capability_menu_ref="menu-c", base=tmp_path)
    assert r.output_artifact_ref

def test_missing_body_deferred():
    with pytest.raises(AgentTurnDispatchError) as exc:
        dispatch_internal_action(run_id="run-c", turn_index=1, decision=_decision("propose_draft"),
            turn_intent=_intent("propose_draft", ""), observe_snapshot_ref="snap-c")
    assert "BODY_MISSING" in str(exc.value) or "DEFERRED" in str(exc.value)

def test_provider_missing_deferred():
    intent = type(_intent("propose_draft", VALID_DRAFT))(**{**_intent("propose_draft", VALID_DRAFT).__dict__, "provider_receipt_ref": None})
    with pytest.raises(AgentTurnDispatchError):
        dispatch_internal_action(run_id="run-c", turn_index=1, decision=_decision("propose_draft"),
            turn_intent=intent, observe_snapshot_ref="snap-c")

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")

def test_turn_receipt_records_quality_refs(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setattr("hg_runtime.agent_turn_engine.context_builder._collect_provider_refs",
        lambda **kwargs: ["prov-test"])
    req = build_agent_turn_request(agent_id="c-b", run_id="run-content-1", allow_provider=True)
    out_json = json.dumps({
        "observation_summary": "Draft cycle.",
        "reasoning_summary": "Proposing draft.",
        "chosen_action": "propose_draft",
        "action_params": {"body": VALID_DRAFT},
        "alternatives_considered": [],
        "uncertainty": "low",
        "operator_questions": [],
        "scope_requests": [],
    })
    def _invoke(_p, _r):
        return out_json
    out = run_single_agent_turn(req, provider_invoke=_invoke, base=tmp_path)
    from hg_runtime.agent_turn_engine.schema import AgentTurnResult
    assert isinstance(out, AgentTurnResult)
    assert out.dispatch_result_ref
