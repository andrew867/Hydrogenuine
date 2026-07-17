"""Redaction guard tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.redaction import contains_hidden_cot, contains_secret  # noqa: E402
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent  # noqa: E402
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402


def test_secret_redaction_rejects_bearer_token():
    assert contains_secret({"note": "Authorization: Bearer abc123xyz"})


def test_cot_guard_rejects_scratchpad():
    assert contains_hidden_cot({"scratchpad": "private chain of thought"})


def test_reasoning_summary_allowed():
    menu = build_capability_menu(runtime_mode="local_dev")
    from hg_runtime.agent_zero_state.types import TurnIntentVerdict

    verdict, intent = build_turn_intent(
        agent_id="a1",
        turn_index=1,
        chosen_action="synthesize_notes",
        menu=menu,
        observation_summary="saw two posts",
        why_this_action="continuity",
        uncertainty="moderate",
    )
    assert verdict == TurnIntentVerdict.GREEN_TURN_INTENT_VALID
    assert intent.observation_summary
