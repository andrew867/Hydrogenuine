"""Reasoning engine integration tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot  # noqa: E402
from hg_runtime.agent_zero_state.state import create_agent_state  # noqa: E402
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict  # noqa: E402
from hg_runtime.agent_zero_reasoning.reasoning_engine import produce_turn_intent  # noqa: E402
from hg_runtime.agent_zero_reasoning.schema import ReasoningFailure, ReasoningResult, ReasoningVerdict  # noqa: E402

VALID_OUTPUT = json.dumps({
    "observation_summary": "Quiet cycle.",
    "reasoning_summary": "Choosing rest.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [{"action": "observe_social", "why_not": "no items"}],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_INFER_DRY_RUN", "0")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)


def _fixtures():
    _, state = create_agent_state(agent_id="agent-eng", runtime_mode="local_dev", run_id="run-1")
    verdict, snap = build_observe_snapshot(
        agent_id="agent-eng",
        turn_index=1,
        runtime_mode="local_dev",
        provider_reality_refs=["prov-1"],
        live_read_receipt_refs=["live-1"],
    )
    assert verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY
    menu = build_capability_menu(runtime_mode="local_dev", operator_presence="operator_present")
    return state, snap, menu


def test_provider_unavailable_returns_reasoning_failure(monkeypatch):
    state, snap, menu = _fixtures()
    out = produce_turn_intent(agent_state=state, observe_snapshot=snap, capability_menu=menu)
    assert isinstance(out, ReasoningFailure)
    assert out.verdict == ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE


def test_valid_test_double_creates_turn_intent():
    state, snap, menu = _fixtures()

    def _invoke(_prompt, _receipt):
        return VALID_OUTPUT

    out = produce_turn_intent(
        agent_state=state,
        observe_snapshot=snap,
        capability_menu=menu,
        provider_invoke=_invoke,
    )
    assert isinstance(out, ReasoningResult)
    assert out.provider_receipt_ref
    assert out.turn_intent.chosen_action == "rest_turn"
    assert out.turn_intent.provider_receipt_ref == out.provider_receipt_ref


def test_reasoning_result_has_provider_receipt_ref():
    state, snap, menu = _fixtures()

    def _invoke(_prompt, _receipt):
        return VALID_OUTPUT

    out = produce_turn_intent(
        agent_state=state,
        observe_snapshot=snap,
        capability_menu=menu,
        provider_invoke=_invoke,
    )
    assert isinstance(out, ReasoningResult)
    assert out.provider_receipt_ref.startswith("provider-")


def test_empty_provider_output_returns_failure():
    state, snap, menu = _fixtures()

    def _invoke(_prompt, _receipt):
        return ""

    out = produce_turn_intent(
        agent_state=state,
        observe_snapshot=snap,
        capability_menu=menu,
        provider_invoke=_invoke,
    )
    assert isinstance(out, ReasoningFailure)
    assert out.verdict == ReasoningVerdict.RED_REASONING_EMPTY_OUTPUT
