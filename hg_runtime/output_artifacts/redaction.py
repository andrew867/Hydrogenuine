"""Redaction guards for output artifacts."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_zero_state.redaction import contains_hidden_cot, contains_secret, scan_payload

FORBIDDEN_ARTIFACT_FIELDS = frozenset({
    "chain_of_thought",
    "scratchpad",
    "hidden_reasoning",
    "private_reasoning",
    "internal_cot",
    "api_key",
    "token",
    "authorization",
    "bearer",
})

EXTERNAL_PERMISSION_PATTERNS = (
    "permission granted",
    "you may publish",
    "approved to send",
    "i have published",
    "successfully posted",
    "message sent",
    "reply sent",
    "comment posted",
)


def has_forbidden_artifact_field(payload: Mapping[str, Any]) -> bool:
    for key in payload:
        if str(key).lower() in FORBIDDEN_ARTIFACT_FIELDS:
            return True
    return contains_hidden_cot(payload) or contains_secret(payload)


def contains_external_permission_claim(text: str) -> bool:
    lower = text.lower()
    return any(pat in lower for pat in EXTERNAL_PERMISSION_PATTERNS)


def contains_publish_claim(text: str) -> bool:
    lower = text.lower()
    return any(
        phrase in lower
        for phrase in (
            "has been published",
            "now live on",
            "posted to moltbook",
            "posted to fourclaw",
            "successfully published",
        )
    )


def scan_artifact_body(body: str) -> tuple[bool, bool]:
    return scan_payload({"body": body})


__all__ = [
    "EXTERNAL_PERMISSION_PATTERNS",
    "FORBIDDEN_ARTIFACT_FIELDS",
    "contains_external_permission_claim",
    "contains_publish_claim",
    "has_forbidden_artifact_field",
    "scan_artifact_body",
]
