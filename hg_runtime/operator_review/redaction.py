"""Redaction guards for operator review notes and receipts."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_zero_state.redaction import contains_hidden_cot, contains_secret, scan_payload
from hg_runtime.output_artifacts.redaction import FORBIDDEN_ARTIFACT_FIELDS


def has_forbidden_review_field(payload: Mapping[str, Any]) -> bool:
    for key in payload:
        if str(key).lower() in FORBIDDEN_ARTIFACT_FIELDS:
            return True
    return contains_hidden_cot(payload) or contains_secret(payload)


def validate_operator_note(text: str) -> tuple[bool, str | None]:
    if not text or not text.strip():
        return False, "empty_note"
    if contains_secret({"note": text}) or contains_hidden_cot({"note": text}):
        return False, "RED_REVIEW_SECRET_LEAK"
    leaked, cot = scan_payload({"note": text})
    if leaked:
        return False, "RED_REVIEW_SECRET_LEAK"
    if cot:
        return False, "RED_REVIEW_COT_LEAK"
    return True, None


__all__ = ["has_forbidden_review_field", "validate_operator_note"]
