"""Reasoning CoT and secret storage guards."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_reasoning.output_parser import parse_reasoning_output  # noqa: E402
from hg_runtime.agent_zero_reasoning.reasoning_receipts import build_reasoning_receipt_from_result  # noqa: E402
from hg_runtime.agent_zero_reasoning.schema import ReasoningResult, ReasoningVerdict, new_result_id  # noqa: E402
from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent  # noqa: E402

BASE = {
    "observation_summary": "ok",
    "reasoning_summary": "because",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
}


def test_no_hidden_cot_stored_in_parser():
    with pytest.raises(Exception):
        parse_reasoning_output(json.dumps({**BASE, "hidden_reasoning": "secret thoughts"}))


def test_no_secrets_stored_in_parser():
    with pytest.raises(Exception):
        parse_reasoning_output(json.dumps({**BASE, "bearer": "Bearer abc.def.ghi"}))


def test_reasoning_receipt_payload_has_no_raw_secrets():
    menu = build_capability_menu(runtime_mode="local_dev")
    _, intent = build_turn_intent(
        agent_id="agent-1",
        turn_index=1,
        chosen_action="rest_turn",
        menu=menu,
        observation_summary="ok",
        provider_receipt_ref="prov-1",
    )
    result = ReasoningResult(
        result_id=new_result_id(),
        request_id="req-1",
        provider_receipt_ref="prov-1",
        turn_intent=intent,
        reasoning_summary="rest",
        raw_model_output_hash="hash-only",
        parsed_output_hash="parsed-hash",
        verdict=ReasoningVerdict.GREEN_REASONING_INTENT_VALID,
        created_at="2026-06-17T00:00:00+00:00",
    ).with_hash()
    receipt = build_reasoning_receipt_from_result(
        request_id="req-1",
        observe_snapshot_ref="snap-1",
        capability_menu_ref=menu.menu_id,
        agent_state_ref="state-1",
        prompt_hash="prompt-1",
        result=result,
    )
    payload = receipt.to_payload()
    assert "Bearer" not in json.dumps(payload)
    assert "scratchpad" not in payload
