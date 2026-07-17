"""Internal dispatch tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu
from hg_runtime.capability_broker.schema import BrokerDecision, BrokerDecisionStatus, BrokerVerdict
from hg_runtime.agent_turn_engine.errors import AgentTurnDispatchError
from hg_runtime.agent_turn_engine.internal_dispatch import InternalDispatchVerdict, dispatch_internal_action

def _menu():
    return build_capability_menu(runtime_mode="local_dev", provider_available=True, live_read_available=True)

def _intent(action):
    _, intent = build_turn_intent(agent_id="d-a", turn_index=1, chosen_action=action, menu=_menu(),
        observation_summary="t", provider_receipt_ref="p1")
    return intent

def _decision(action, *, admitted=True, status=BrokerDecisionStatus.ADMIT_INTERNAL):
    return BrokerDecision(decision_id="dec-1", request_id="req-1", agent_id="d-a", run_id="run-d",
        turn_index=1, chosen_action=action, status=status, admitted=admitted, refused=not admitted,
        deferred=False, internal_only=True, external_side_effect=False, refusal_reasons=[],
        requirements_checked={}, policy_refs=[], created_at="2026-06-17T00:00:00+00:00",
        verdict=BrokerVerdict.GREEN_BROKER_ADMITTED_INTERNAL).with_hash()

def test_rest_dispatch(tmp_path):
    r = dispatch_internal_action(run_id="run-d", turn_index=1, decision=_decision("rest_turn"),
        turn_intent=_intent("rest_turn"), observe_snapshot_ref="snap-1", base=tmp_path)
    assert r.verdict == InternalDispatchVerdict.GREEN_INTERNAL_DISPATCH_COMPLETE
    assert not r.external_side_effect

def test_witness_dispatch(tmp_path):
    r = dispatch_internal_action(run_id="run-d", turn_index=1, decision=_decision("witness_turn", status=BrokerDecisionStatus.WITNESS),
        turn_intent=_intent("witness_turn"), observe_snapshot_ref="snap-1", base=tmp_path)
    assert r.witness_receipt_ref

def test_scope_dispatch(tmp_path):
    intent = type(_intent("request_more_scope"))(**{**_intent("request_more_scope").__dict__, "scope_requests": ["scope-1"]})
    r = dispatch_internal_action(run_id="run-d", turn_index=1,
        decision=_decision("request_more_scope", status=BrokerDecisionStatus.REQUEST_SCOPE),
        turn_intent=intent, observe_snapshot_ref="snap-1", base=tmp_path)
    assert r.scope_request_refs

def test_operator_question_local_only(tmp_path):
    intent = type(_intent("propose_operator_question"))(**{**_intent("propose_operator_question").__dict__, "operator_questions": ["q1"]})
    r = dispatch_internal_action(run_id="run-d", turn_index=1,
        decision=_decision("propose_operator_question", status=BrokerDecisionStatus.REQUEST_OPERATOR),
        turn_intent=intent, observe_snapshot_ref="snap-1", base=tmp_path)
    assert r.operator_question_refs
    assert r.artifact_ref

def test_observe_read_only(tmp_path):
    r = dispatch_internal_action(run_id="run-d", turn_index=1, decision=_decision("observe_social"),
        turn_intent=_intent("observe_social"), observe_snapshot_ref="snap-1",
        live_read_receipt_refs=["live-1"], base=tmp_path)
    assert r.verdict == InternalDispatchVerdict.YELLOW_INTERNAL_DISPATCH_READ_ONLY

def test_publish_rejected(tmp_path):
    with pytest.raises(AgentTurnDispatchError):
        dispatch_internal_action(run_id="run-d", turn_index=1, decision=_decision("publish"),
            turn_intent=_intent("rest_turn"), observe_snapshot_ref="snap-1", base=tmp_path)

def test_unsupported_without_body_deferred(tmp_path):
    with pytest.raises(AgentTurnDispatchError):
        dispatch_internal_action(run_id="run-d", turn_index=1, decision=_decision("propose_draft"),
            turn_intent=_intent("rest_turn"), observe_snapshot_ref="snap-1", base=tmp_path)
