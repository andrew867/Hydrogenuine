"""Reasoning receipt tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.capability_menu import build_capability_menu  # noqa: E402
from hg_runtime.agent_zero_state.turn_intent import build_turn_intent  # noqa: E402
from hg_runtime.agent_zero_reasoning.reasoning_receipts import (  # noqa: E402
    build_reasoning_receipt_from_result,
)
from hg_runtime.agent_zero_reasoning.schema import (  # noqa: E402
    ReasoningResult,
    ReasoningVerdict,
    new_result_id,
)


def test_reasoning_receipt_hashes_deterministically():
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
        raw_model_output_hash="raw-hash",
        parsed_output_hash="parsed-hash",
        verdict=ReasoningVerdict.YELLOW_WITNESS_OR_REST_CHOSEN,
        created_at="2026-06-17T00:00:00+00:00",
    ).with_hash()
    receipt_a = build_reasoning_receipt_from_result(
        request_id="req-1",
        observe_snapshot_ref="snap-1",
        capability_menu_ref=menu.menu_id,
        agent_state_ref="state-1",
        prompt_hash="prompt-1",
        result=result,
    )
    receipt_b = build_reasoning_receipt_from_result(
        request_id="req-1",
        observe_snapshot_ref="snap-1",
        capability_menu_ref=menu.menu_id,
        agent_state_ref="state-1",
        prompt_hash="prompt-1",
        result=result,
    )
    assert receipt_a.hash == receipt_b.hash
    assert receipt_a.provider_receipt_ref == "prov-1"
