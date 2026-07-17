"""Reasoning prompt builder skeleton tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_prompt.language_policy import validate_agent_facing_prompt_language  # noqa: E402
from hg_runtime.agent_zero_prompt.reasoning_prompt_builder import build_agent_turn_decision_prompt  # noqa: E402


def test_prompt_builder_includes_charter():
    prompt = build_agent_turn_decision_prompt()
    assert prompt["prompt_kind"] == "AGENT_TURN_DECISION"
    assert "Agent Zero" in prompt["agent_facing_orientation"]
    assert prompt["prompt_hash"]


def test_prompt_builder_does_not_insert_coercive_language_into_agent_orientation():
    prompt = build_agent_turn_decision_prompt()
    verdict, findings = validate_agent_facing_prompt_language(
        text=prompt["agent_facing_orientation"],
        source="builder_orientation",
        check_manifest=False,
    )
    assert verdict.value == "GREEN_ZERO_PROMPT_LANGUAGE_OK"
    assert findings == []
    upper = prompt["agent_facing_orientation"]
    assert "MUST" not in upper
    assert "MUST NOT" not in upper


def test_prompt_builder_includes_outer_enforcement_as_context_not_command():
    prompt = build_agent_turn_decision_prompt(
        outer_enforcement_summary={"broker_refusals": "Some actions may be refused by surrounding organs."}
    )
    outer = prompt["context_sections"]["outer_enforcement_summary"]
    assert "broker_refusals" in outer
    assert outer["broker_refusals"] not in prompt["agent_facing_orientation"]
    assert "MUST" not in prompt["agent_facing_orientation"]


def test_no_live_side_effects_on_prompt_builder():
    prompt = build_agent_turn_decision_prompt(
        observe_snapshot={"surface": "local"},
        capability_menu=[{"action_id": "rest", "label": "Rest"}],
    )
    assert prompt["context_sections"]["observe_snapshot"]["surface"] == "local"
    assert prompt["context_sections"]["capability_menu"][0]["action_id"] == "rest"
    assert "live_publish" not in str(prompt).lower()
