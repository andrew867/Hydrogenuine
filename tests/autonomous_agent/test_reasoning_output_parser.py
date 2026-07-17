"""Reasoning output parser tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_reasoning.errors import ReasoningParseError  # noqa: E402
from hg_runtime.agent_zero_reasoning.output_parser import parse_reasoning_output  # noqa: E402

VALID = {
    "observation_summary": "Feeds are quiet.",
    "reasoning_summary": "Rest is appropriate.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [{"action": "observe_social", "why_not": "no items"}],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
}


def test_parser_accepts_valid_json_object():
    parsed = parse_reasoning_output(json.dumps(VALID))
    assert parsed["chosen_action"] == "rest_turn"


def test_parser_rejects_empty_output():
    with pytest.raises(ReasoningParseError):
        parse_reasoning_output("")


def test_parser_rejects_invalid_json():
    with pytest.raises(ReasoningParseError):
        parse_reasoning_output("{not json")


def test_parser_rejects_hidden_cot_fields():
    bad = {**VALID, "scratchpad": "hidden thoughts"}
    with pytest.raises(ReasoningParseError):
        parse_reasoning_output(json.dumps(bad))


def test_parser_rejects_secret_like_fields():
    bad = {**VALID, "api_key": "sk-secret"}
    with pytest.raises(ReasoningParseError):
        parse_reasoning_output(json.dumps(bad))
