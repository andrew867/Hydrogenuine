"""Static organ edge filter — blocks naked messages without TEP envelope."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash

_REQUIRED_ENVELOPE_FIELDS = (
    "source",
    "target",
    "message_class",
    "authority_semantics",
    "confidence",
    "ambiguity",
    "ttl_expiry",
    "redaction_class",
    "evidence_refs",
    "envelope_hash",
    "replay_identity",
)


def is_tep_wrapped(message: dict[str, Any]) -> bool:
    envelope = message.get("tep_envelope")
    if not isinstance(envelope, dict):
        return False
    return all(field in envelope for field in _REQUIRED_ENVELOPE_FIELDS)


def filter_naked_message(message: dict[str, Any]) -> dict[str, object]:
    """Fail closed on naked bus messages — advisory filter only."""
    if is_tep_wrapped(message):
        return {
            "status": "filtered",
            "filter_action": "pass_through",
            "naked_message_blocked": False,
            "permission_granted": False,
            "authority_created": False,
            "edge_filter_is_advisory_only": True,
        }
    return {
        "status": "blocked",
        "filter_action": "quarantine",
        "naked_message_blocked": True,
        "reason_code": "arm.edge_filter.naked_message_blocked",
        "permission_granted": False,
        "authority_created": False,
        "edge_filter_is_advisory_only": True,
    }


def envelope_hash_for_fixture(source: str, target: str, replay_identity: str) -> str:
    return canonical_hash(
        {
            "source": source,
            "target": target,
            "replay_identity": replay_identity,
            "fixture_only": True,
        }
    )


def make_fixture_envelope(*, source: str, target: str, replay_identity: str) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "message_class": "arm.fixture.bus",
        "authority_semantics": "non_authority",
        "confidence": 0.5,
        "ambiguity": 0.1,
        "ttl_expiry": "2026-06-15T00:00:00Z",
        "redaction_class": "fixture",
        "evidence_refs": [],
        "envelope_hash": envelope_hash_for_fixture(source, target, replay_identity),
        "replay_identity": replay_identity,
    }


__all__ = [
    "filter_naked_message",
    "is_tep_wrapped",
    "make_fixture_envelope",
    "envelope_hash_for_fixture",
]
