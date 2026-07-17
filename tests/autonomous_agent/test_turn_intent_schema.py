"""TurnIntent schema tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent  # noqa: E402
from hg_runtime.agent_zero_state.types import TurnIntentVerdict  # noqa: E402


def _menu():
    return build_capability_menu(runtime_mode="local_dev", operator_presence="operator_present")


def test_turn_intent_rejects_unknown_action():
    verdict, _ = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="publish",
        menu=_menu(),
        observation_summary="test",
    )
    assert verdict == TurnIntentVerdict.RED_TURN_INTENT_UNKNOWN_ACTION


def test_turn_intent_allows_request_more_scope():
    verdict, intent = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="request_more_scope",
        menu=_menu(),
        observation_summary="need broader read",
        scope_requests=["scope-req-1"],
    )
    assert verdict == TurnIntentVerdict.GREEN_TURN_INTENT_VALID
    assert intent.chosen_action == "request_more_scope"


def test_turn_intent_allows_rest_turn():
    verdict, intent = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="rest_turn",
        menu=_menu(),
        observation_summary="choosing rest",
        why_this_action="limits reached",
    )
    assert verdict == TurnIntentVerdict.GREEN_TURN_INTENT_VALID


def test_turn_intent_rejects_hidden_cot():
    verdict, _ = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="rest_turn",
        menu=_menu(),
        observation_summary="x",
        extra_fields={"scratchpad": "hidden thoughts"},
    )
    assert verdict == TurnIntentVerdict.RED_TURN_INTENT_COT_LEAK


def test_turn_intent_rejects_secrets():
    verdict, _ = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="rest_turn",
        menu=_menu(),
        observation_summary="Bearer sk-secret-token",
    )
    assert verdict == TurnIntentVerdict.RED_TURN_INTENT_SECRET_LEAK
