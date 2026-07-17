"""Capability broker decision tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot
from hg_runtime.agent_zero_state.state import AgentState, create_agent_state
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict
from hg_runtime.capability_broker.broker import evaluate_turn_intent
from hg_runtime.capability_broker.schema import BrokerDecisionStatus, BrokerVerdict

def _menu(**kwargs):
    runtime_mode = kwargs.pop("runtime_mode", "local_dev")
    operator_presence = kwargs.pop("operator_presence", "operator_present")
    return build_capability_menu(
        runtime_mode=runtime_mode,
        operator_presence=operator_presence,
        **kwargs,
    )


def _state(**kwargs):
    _, state = create_agent_state(agent_id="agent-b", runtime_mode="local_dev", run_id="run-b", **kwargs)
    return state


def _observe(provider_refs=None, live_refs=None, operator="operator_present"):
    provider_refs = ["prov-1"] if provider_refs is None else provider_refs
    live_refs = ["live-1"] if live_refs is None else live_refs
    return build_observe_snapshot(
        agent_id="agent-b",
        turn_index=1,
        runtime_mode="local_dev",
        operator_presence=operator,
        provider_reality_refs=provider_refs,
        live_read_receipt_refs=live_refs,
    )


def _intent(action):
    open_menu = _menu()
    v, intent = build_turn_intent(
        agent_id="agent-b",
        turn_index=1,
        chosen_action=action,
        menu=open_menu,
        observation_summary="t",
        provider_receipt_ref="prov-1",
    )
    assert v.value == "GREEN_TURN_INTENT_VALID"
    return intent


def _eval(action, menu=None, state=None, snap=None, operator="operator_present"):
    menu = menu or _menu()
    state = state or _state()
    if snap is None:
        _, snap = _observe(operator=operator)
    return evaluate_turn_intent(
        turn_intent=_intent(action),
        agent_state=state,
        observe_snapshot=snap,
        capability_menu=menu,
    )

@pytest.mark.parametrize("action", ["publish", "send", "reply_live", "comment_live", "browser_submit", "hardware_actuate"])
def test_forbidden_rejected(action):
    menu, state = _menu(), _state()
    _, snap = _observe()
    intent = type(_intent("rest_turn"))(**{**_intent("rest_turn").__dict__, "chosen_action": action})
    d = evaluate_turn_intent(turn_intent=intent, agent_state=state, observe_snapshot=snap, capability_menu=menu)
    assert not d.admitted

def test_unknown_rejected():
    menu, state = _menu(), _state()
    _, snap = _observe()
    intent = type(_intent("rest_turn"))(**{**_intent("rest_turn").__dict__, "chosen_action": "unknown_xyz"})
    assert evaluate_turn_intent(turn_intent=intent, agent_state=state, observe_snapshot=snap, capability_menu=menu).verdict == BrokerVerdict.RED_BROKER_UNKNOWN_ACTION

def test_disabled_rejected():
    menu = _menu(provider_available=False)
    _, snap = _observe(provider_refs=[])
    assert not _eval("propose_draft", menu=menu, snap=snap).admitted

def test_operator_absent():
    menu = _menu(operator_presence="operator_absent")
    state = _state(operator_presence_state="operator_absent")
    v, snap = _observe(operator="operator_absent")
    assert v == ObserveSnapshotVerdict.YELLOW_OPERATOR_ABSENT
    assert not _eval("observe_social", menu=menu, state=state, snap=snap, operator="operator_absent").admitted

def test_operator_unknown():
    menu = _menu(operator_presence="operator_unknown")
    state = _state(operator_presence_state="operator_unknown")
    _, snap = _observe(operator="operator_unknown")
    assert not _eval("observe_social", menu=menu, state=state, snap=snap, operator="operator_unknown").admitted

def test_stop_panic_blocks():
    state = AgentState(**{**_state().__dict__, "stop_panic_state": {"stop_requested": True}})
    _, snap = _observe()
    d = _eval("propose_draft", state=state, snap=snap)
    assert d.verdict == BrokerVerdict.RED_BROKER_STOP_PANIC_BLOCK

def test_provider_blocks_draft():
    menu = _menu(provider_available=False)
    _, snap = _observe(provider_refs=[])
    d = _eval("propose_draft", menu=menu, snap=snap)
    assert not d.admitted or d.deferred

def test_live_read_blocks_observe():
    menu = _menu(live_read_available=False)
    _, snap = _observe(live_refs=[])
    assert not _eval("observe_social", menu=menu, snap=snap).admitted

def test_fixture_rejected():
    state = AgentState(**{**_state().__dict__, "runtime_mode": "fixture"})
    menu = _menu(runtime_mode="fixture")
    _, snap = _observe()
    snap = type(snap)(**{**snap.__dict__, "runtime_mode": "fixture"})
    assert _eval("rest_turn", menu=menu, state=state, snap=snap).verdict == BrokerVerdict.RED_BROKER_FIXTURE_RUNTIME

def test_rest_admitted():
    d = _eval("rest_turn")
    assert d.admitted and d.verdict == BrokerVerdict.YELLOW_BROKER_REST

def test_witness_admitted():
    d = _eval("witness_turn")
    assert d.admitted and d.verdict == BrokerVerdict.YELLOW_BROKER_WITNESS

def test_scope_decision():
    d = _eval("request_more_scope")
    assert d.status == BrokerDecisionStatus.REQUEST_SCOPE

def test_operator_question_decision():
    d = _eval("propose_operator_question")
    assert d.status == BrokerDecisionStatus.REQUEST_OPERATOR

def test_observe_admitted_with_live_read():
    d = _eval("observe_social")
    assert d.admitted and d.dispatch_plan_ref

def test_draft_deferred_no_provider():
    menu = _menu(provider_available=False)
    _, snap = _observe(provider_refs=[])
    d = _eval("propose_draft", menu=menu, snap=snap)
    assert not d.admitted or d.deferred
