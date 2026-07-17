"""Reasoning prompt builder skeleton — no provider calls."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_prompt.charter import (
    build_zero_orientation_block,
    compute_prompt_hash,
    load_zero_charter,
    load_zero_witness_extension,
)

OUTER_ENFORCEMENT_SUMMARY_DEFAULT = {
    "broker_refusals": "Some actions may be refused by surrounding organs.",
    "broker_records": "The broker records refusals.",
    "operator_review": "The operator reviews surfaced artifacts.",
    "external_actions": "External actions are mediated outside this prompt.",
    "fixture_boundary": "Fixture data is gated by runtime mode.",
    "stop_panic": "STOP and PANIC remain available to the operator.",
}


def build_agent_turn_decision_prompt(
    *,
    charter_text: str | None = None,
    observe_snapshot: dict | None = None,
    capability_menu: list[dict] | None = None,
    prior_turn_summaries: list[dict] | None = None,
    outer_enforcement_summary: dict | None = None,
) -> dict[str, Any]:
    """Prepare structured prompt sections for Phase 6 reasoning engine."""
    charter = charter_text or load_zero_charter().text.strip()
    orientation = build_zero_orientation_block()
    observe_snapshot = observe_snapshot or {}
    capability_menu = capability_menu or []
    prior_turn_summaries = prior_turn_summaries or []
    outer = {**OUTER_ENFORCEMENT_SUMMARY_DEFAULT, **(outer_enforcement_summary or {})}

    payload = {
        "prompt_kind": "AGENT_TURN_DECISION",
        "orientation_block": orientation,
        "agent_facing_orientation": charter,
        "context_sections": {
            "observe_snapshot": observe_snapshot,
            "capability_menu": capability_menu,
            "prior_turn_summaries": prior_turn_summaries,
            "outer_enforcement_summary": outer,
        },
        "response_shape_hint": {
            "observation_summary": "string",
            "reasoning": "string",
            "chosen_action": "action_id",
            "action_params": {},
            "alternatives_considered": [],
            "why_not_others": "string",
            "open_threads_update": [],
            "operator_questions": [],
            "scope_requests": [],
        },
        "prompt_hash": compute_prompt_hash(charter),
    }
    return payload


__all__ = [
    "OUTER_ENFORCEMENT_SUMMARY_DEFAULT",
    "build_agent_turn_decision_prompt",
    "build_zero_orientation_block",
    "load_zero_witness_extension",
]
