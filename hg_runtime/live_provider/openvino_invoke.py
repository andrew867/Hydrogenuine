"""Default OpenVINO invoke for Agent Zero reasoning — uses repo Windows provider."""

from __future__ import annotations

import json
import re
from typing import Any

from hg_runtime.agent_zero_reasoning.output_parser import parse_reasoning_output
from hg_runtime.live_provider.local_provider_clients import complete_openai_compatible
from hg_runtime.live_provider.openvino_config import openvino_endpoint_base, openvino_model_id
from hg_runtime.live_provider.errors import LiveProviderUnavailable


def _allowed_actions(prompt_payload: dict[str, Any]) -> list[str]:
    sections = prompt_payload.get("context_sections") or {}
    menu = sections.get("capability_menu") or []
    actions: list[str] = []
    for a in menu:
        if not isinstance(a, dict):
            continue
        action_id = str(a.get("action_id") or a.get("id") or "").strip()
        if action_id and a.get("enabled", True):
            actions.append(action_id)
    return actions


def _salvage_turn_json(raw_text: str, *, allowed_actions: list[str]) -> dict[str, Any] | None:
    text = (raw_text or "").strip()
    if not text:
        return None
    action_match = re.search(r'"chosen_action"\s*:\s*"([^"]+)"', text)
    chosen = action_match.group(1).strip() if action_match else ""
    if chosen not in allowed_actions:
        chosen = allowed_actions[0] if allowed_actions else "rest_turn"
    obs_match = re.search(r'"observation_summary"\s*:\s*"([^"]*)"', text)
    observation = obs_match.group(1).strip() if obs_match and obs_match.group(1).strip() else "local autonomous session active"
    reason_match = re.search(r'"reasoning_summary"\s*:\s*"([^"]*)', text)
    reasoning = reason_match.group(1).strip() if reason_match else ""
    if not reasoning:
        reasoning = f"Selected {chosen} for this bounded hands-off turn."
    reasoning = re.split(r'"\s*,\s*"', reasoning)[0][:240]
    alt = next((a for a in allowed_actions if a != chosen), "rest_turn")
    return {
        "observation_summary": observation,
        "reasoning_summary": reasoning,
        "chosen_action": chosen,
        "action_params": {},
        "alternatives_considered": [{"action": alt, "why_not": "not selected this turn"}],
        "uncertainty": "medium",
        "operator_questions": [],
        "scope_requests": [],
    }


def _format_turn_decision_prompt(prompt_payload: dict[str, Any]) -> str:
    """Compact agent-facing prompt for small local models."""
    sections = prompt_payload.get("context_sections") or {}
    observe = sections.get("observe_snapshot") or {}
    observe_summary = str(observe.get("summary") or observe.get("snapshot_verdict") or "local_dev session")
    actions = _allowed_actions(prompt_payload) or ["rest_turn", "witness_turn"]
    schema = (
        '{"observation_summary":"...","reasoning_summary":"...",'
        '"chosen_action":"ACTION","action_params":{},'
        '"alternatives_considered":[{"action":"OTHER","why_not":"..."}],'
        '"uncertainty":"low","operator_questions":[],"scope_requests":[]}'
    )

    return (
        "You are Agent Zero. Return one compact JSON object only.\n"
        f"Context: {observe_summary}\n"
        f"Pick one enabled action from: {', '.join(actions)}\n"
        f"Shape: {schema}\n"
        "Keep every string under 120 chars. Use reasoning_summary field name."
    )


def invoke_openvino_turn_decision(prompt_payload: dict[str, Any], _receipt) -> str:
    """Invoke local OpenVINO provider for turn decision output."""
    actions = _allowed_actions(prompt_payload) or ["rest_turn", "witness_turn"]
    user_content = _format_turn_decision_prompt(prompt_payload)
    result = complete_openai_compatible(
        openvino_endpoint_base(),
        model_id=openvino_model_id(),
        prompt=user_content,
        json_mode=True,
        timeout=300.0,
        max_tokens=512,
    )
    if not result.get("ok"):
        raise LiveProviderUnavailable(result.get("failure_reason") or "openvino invoke failed")
    text = str(result.get("output_text") or "").strip()
    if not text:
        raise LiveProviderUnavailable("empty openvino output")
    try:
        parsed = parse_reasoning_output(text)
        proposed = parsed["chosen_action"]
        if proposed not in actions:
            parsed = {
                **parsed,
                "chosen_action": actions[0],
                "reasoning_summary": (
                    f"{parsed['reasoning_summary']} "
                    f"(provider proposed {proposed}; remapped to {actions[0]})"
                )[:240],
            }
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        salvaged = _salvage_turn_json(text, allowed_actions=actions)
        if not salvaged:
            raise LiveProviderUnavailable("openvino output not parseable")
        return json.dumps(salvaged, ensure_ascii=False)


__all__ = ["invoke_openvino_turn_decision"]
