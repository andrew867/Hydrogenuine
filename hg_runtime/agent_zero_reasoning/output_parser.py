"""Parse and normalize model reasoning output."""

from __future__ import annotations

import json
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.agent_zero_reasoning.errors import ReasoningParseError
from hg_runtime.agent_zero_reasoning.redaction import (
    FORBIDDEN_OUTPUT_FIELDS,
    MARKDOWN_JSON_BLOCK,
    scan_reasoning_payload,
)

REQUIRED_FIELDS = (
    "observation_summary",
    "reasoning_summary",
    "chosen_action",
    "action_params",
    "alternatives_considered",
    "uncertainty",
    "operator_questions",
    "scope_requests",
)

MAX_FIELD_LEN = 8000


def _extract_json_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        raise ReasoningParseError("empty output", kind="empty")
    if text.startswith("{") and text.endswith("}"):
        return text
    match = MARKDOWN_JSON_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1].strip()
    raise ReasoningParseError("non-json output", kind="invalid_json")


def parse_reasoning_output(raw_text: str) -> dict[str, Any]:
    """Parse provider output into a JSON object."""
    try:
        json_text = _extract_json_text(raw_text)
        obj = json.loads(json_text)
    except ReasoningParseError:
        raise
    except json.JSONDecodeError as exc:
        raise ReasoningParseError(f"invalid json: {exc}", kind="invalid_json") from exc
    if not isinstance(obj, dict):
        raise ReasoningParseError("output must be json object", kind="invalid_json")
    return normalize_reasoning_output(obj)


def normalize_reasoning_output(obj: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize parsed reasoning output."""
    if "reasoning_summary" not in obj and obj.get("reasoning"):
        obj = {**obj, "reasoning_summary": obj["reasoning"]}

    has_secret, has_cot, has_forbidden = scan_reasoning_payload(obj)
    if has_secret:
        raise ReasoningParseError("secret in output", kind="secret")
    if has_cot or has_forbidden:
        raise ReasoningParseError("hidden cot or forbidden field", kind="cot")

    for field in REQUIRED_FIELDS:
        if field not in obj:
            raise ReasoningParseError(f"missing field: {field}", kind="missing_field")

    observation = str(obj["observation_summary"]).strip()
    reasoning = str(obj["reasoning_summary"]).strip()
    chosen = str(obj["chosen_action"]).strip()
    uncertainty = str(obj["uncertainty"]).strip()

    if not observation or not reasoning or not chosen or not uncertainty:
        raise ReasoningParseError("empty required string field", kind="empty")

    if not isinstance(obj["action_params"], dict):
        raise ReasoningParseError("action_params must be object", kind="invalid_shape")
    if not isinstance(obj["alternatives_considered"], list):
        raise ReasoningParseError("alternatives_considered must be list", kind="invalid_shape")
    if not isinstance(obj["operator_questions"], list):
        raise ReasoningParseError("operator_questions must be list", kind="invalid_shape")
    if not isinstance(obj["scope_requests"], list):
        raise ReasoningParseError("scope_requests must be list", kind="invalid_shape")

    for alt in obj["alternatives_considered"]:
        if not isinstance(alt, dict):
            raise ReasoningParseError("alternative must be object", kind="invalid_shape")
        if "action" not in alt or "why_not" not in alt:
            raise ReasoningParseError("alternative missing action/why_not", kind="missing_field")

    normalized = {
        "observation_summary": observation[:MAX_FIELD_LEN],
        "reasoning_summary": reasoning[:MAX_FIELD_LEN],
        "chosen_action": chosen,
        "action_params": dict(obj["action_params"]),
        "alternatives_considered": [
            {"action": str(a["action"]).strip(), "why_not": str(a["why_not"]).strip()[:MAX_FIELD_LEN]}
            for a in obj["alternatives_considered"]
        ],
        "uncertainty": uncertainty[:MAX_FIELD_LEN],
        "operator_questions": [str(q).strip()[:MAX_FIELD_LEN] for q in obj["operator_questions"] if str(q).strip()],
        "scope_requests": [str(s).strip()[:MAX_FIELD_LEN] for s in obj["scope_requests"] if str(s).strip()],
    }
    if "open_threads_update" in obj:
        if not isinstance(obj["open_threads_update"], list):
            raise ReasoningParseError("open_threads_update must be list", kind="invalid_shape")
        normalized["open_threads_update"] = obj["open_threads_update"]

    for key in obj:
        if str(key).lower() in FORBIDDEN_OUTPUT_FIELDS:
            raise ReasoningParseError(f"forbidden field: {key}", kind="forbidden_field")

    return normalized


def hash_raw_output(raw_text: str) -> str:
    return hash_record({"raw": raw_text})


def hash_parsed_output(parsed: dict[str, Any]) -> str:
    return hash_record(parsed)


__all__ = [
    "REQUIRED_FIELDS",
    "hash_parsed_output",
    "hash_raw_output",
    "normalize_reasoning_output",
    "parse_reasoning_output",
]
