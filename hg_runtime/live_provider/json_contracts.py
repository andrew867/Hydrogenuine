"""JSON contract validation for provider output."""

from __future__ import annotations

import json
from typing import Any

from hg_runtime.live_provider.schema import LiveProviderVerdict


def validate_json_text(text: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    if not text or not str(text).strip():
        return False, None, "empty output"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return False, None, f"invalid json: {exc}"
    if not isinstance(parsed, dict):
        return False, None, "json root must be object"
    return True, parsed, None


def validate_turn_decision_schema(parsed: dict[str, Any]) -> tuple[bool, str | None]:
    required = ("observation_summary", "reasoning_summary", "chosen_action", "action_params")
    missing = [k for k in required if k not in parsed]
    if missing:
        return False, f"missing fields: {', '.join(missing)}"
    if "chain_of_thought" in parsed or "hidden_reasoning" in parsed:
        return False, "hidden cot fields forbidden"
    return True, None


def evaluate_json_output(text: str, *, require_turn_schema: bool = False) -> tuple[bool, bool, LiveProviderVerdict]:
    json_valid, parsed, err = validate_json_text(text)
    if not json_valid:
        return False, False, LiveProviderVerdict.YELLOW_PROVIDER_JSON_INVALID_DEFERRED
    schema_valid = True
    if require_turn_schema:
        schema_valid, schema_err = validate_turn_decision_schema(parsed or {})
        if not schema_valid:
            return True, False, LiveProviderVerdict.YELLOW_PROVIDER_JSON_INVALID_DEFERRED
    return True, schema_valid, LiveProviderVerdict.GREEN_LIVE_PROVIDER_OUTPUT_VALID
