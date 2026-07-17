"""Reasoning engine live provider integration tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_reasoning.reasoning_engine import produce_turn_intent
from hg_runtime.agent_zero_reasoning.schema import ReasoningFailure, ReasoningResult, ReasoningVerdict
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot
from hg_runtime.agent_zero_state.state import create_agent_state

VALID = json.dumps({
    "observation_summary": "Quiet.",
    "reasoning_summary": "Rest.",
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
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")


def _ctx():
    _, state = create_agent_state(agent_id="re-a", run_id="re-run", runtime_mode="local_dev")
    _, snap = build_observe_snapshot(agent_id="re-a", turn_index=1, runtime_mode="local_dev")
    menu = build_capability_menu(runtime_mode="local_dev", provider_available=False)
    return state, snap, menu


def test_provider_unavailable_yellow_failure(monkeypatch):
    monkeypatch.setenv("HG_LIVE_PROVIDER_KIND", "dry_unavailable")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setattr("hg_runtime.model_provider_fabric.routing._openvino_live_available", lambda: False)
    state, snap, menu = _ctx()
    out = produce_turn_intent(agent_state=state, observe_snapshot=snap, capability_menu=menu)
    assert isinstance(out, ReasoningFailure)
    assert out.verdict == ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE
    assert out.provider_receipt_ref


def test_valid_provider_output_with_receipt():
    state, snap, menu = _ctx()

    def _invoke(_p, _r):
        return VALID

    out = produce_turn_intent(agent_state=state, observe_snapshot=snap, capability_menu=menu, provider_invoke=_invoke)
    assert isinstance(out, ReasoningResult)
    assert out.provider_receipt_ref
    assert out.turn_intent.chosen_action == "rest_turn"


def test_empty_provider_output_failure():
    state, snap, menu = _ctx()

    def _invoke(_p, _r):
        return ""

    out = produce_turn_intent(agent_state=state, observe_snapshot=snap, capability_menu=menu, provider_invoke=_invoke)
    assert isinstance(out, ReasoningFailure)


def test_invalid_json_failure():
    state, snap, menu = _ctx()

    def _invoke(_p, _r):
        return "not-json"

    out = produce_turn_intent(agent_state=state, observe_snapshot=snap, capability_menu=menu, provider_invoke=_invoke)
    assert isinstance(out, ReasoningFailure)
    assert out.verdict == ReasoningVerdict.RED_REASONING_INVALID_JSON
