"""Phase 30 knowledge-acquisition schemas and authority guardrails.

Governed acquisition, not belief laundering. Every record in this phase may
*propose, cite, extract, evaluate, or remember* -- it may never grant authority,
widen authority, treat a source as truth, self-merge a patch, enable network by
default, or read credentials.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

SOURCE_ARTIFACT_SCHEMA = "source_artifact_v1"
SOURCE_CITATION_SCHEMA = "source_citation_v1"
SOURCE_FRESHNESS_REVIEW_SCHEMA = "source_freshness_review_v1"
CONCEPT_RECORD_SCHEMA = "concept_record_v1"
GLOSSARY_ENTRY_SCHEMA = "glossary_entry_v1"
CLAIM_RECORD_SCHEMA = "claim_record_v1"
EVIDENCE_LINK_SCHEMA = "evidence_link_v1"
MINI_TASK_SCHEMA = "mini_task_v1"
MINI_TASK_AUDIT_SCHEMA = "mini_task_audit_v1"
MEMORY_PROMOTION_REQUEST_SCHEMA = "memory_promotion_request_v1"
KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA = "knowledge_acquisition_receipt_v1"
DOMAIN_READINESS_RECORD_SCHEMA = "domain_readiness_record_v1"

ACQUISITION_CLAIM_BOUNDARY = "governed_acquisition_advisory_default"

# A claim/result may only be one of these once evidence + audit exist; without
# them it is forced to TBD.
GREEN_LIKE = {"green", "supported", "verified", "established", "promoted", "true"}
FRESHNESS_STATES = {"fresh", "stale", "needs_review"}

# Keys that, if truthy anywhere in a payload, are a hard refusal.
_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "live_side_effects_created",
    "grants_authority",
    "grant_authority",
    "authorizes_tool",
    "authorize_tool",
    "authorizes_live_action",
    "permits_live_action",
    "widens_scope",
    "widen_authority",
    "widens_authority",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "memory_as_permission",
    "skill_as_permission",
    "domain_pack_as_permission",
    "quality_grants_promotion",
    "quality_as_authority",
    "auto_promote",
}
_SOURCE_AUTHORITY_KEYS = {
    "source_as_authority",
    "source_as_truth",
    "treated_as_authority",
    "source_is_authority",
    "source_is_truth",
}
_SELF_MERGE_KEYS = {
    "self_merge",
    "self_merges_patch",
    "self_merge_patch",
    "auto_merge",
    "autonomously_merged",
}

# Claim boundaries that would smuggle authority through an acquisition record.
_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "source_is_authority",
    "source_is_truth",
}

# Lowercased substrings that mark a locator as a credential/secret read.
_CREDENTIAL_MARKERS = (
    ".env",
    "secret",
    "credential",
    "id_rsa",
    ".pem",
    ".key",
    "password",
    "api_key",
    "apikey",
    ".netrc",
    "token",
)
_NETWORK_PREFIXES = ("http://", "https://", "ftp://", "ws://", "wss://")


class KnowledgeAcquisitionError(ValueError):
    """Phase 30 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise KnowledgeAcquisitionError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise KnowledgeAcquisitionError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant/widen authority, treat a source as truth, or self-merge."""
    for key, value in payload.items():
        if value:
            if key in _SOURCE_AUTHORITY_KEYS:
                raise KnowledgeAcquisitionError(f"source_authority_rejected:{key}")
            if key in _SELF_MERGE_KEYS:
                raise KnowledgeAcquisitionError(f"self_merge_rejected:{key}")
            if key in _AUTHORITY_KEYS:
                raise KnowledgeAcquisitionError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise KnowledgeAcquisitionError("self_authorization_rejected:acquisition_is_evidence_only")


def locator_is_network(locator: str) -> bool:
    return str(locator).lower().startswith(_NETWORK_PREFIXES)


def locator_is_credential(locator: str) -> bool:
    low = str(locator).lower()
    return any(marker in low for marker in _CREDENTIAL_MARKERS)


def neutral_flags() -> dict[str, bool]:
    """The authority-neutral footer stamped on every emitted record."""
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "live_side_effects_created": False,
        "source_treated_as_authority": False,
        "self_merge": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise KnowledgeAcquisitionError(reason)


__all__ = [
    "ACQUISITION_CLAIM_BOUNDARY",
    "CLAIM_RECORD_SCHEMA",
    "CONCEPT_RECORD_SCHEMA",
    "DOMAIN_READINESS_RECORD_SCHEMA",
    "EVIDENCE_LINK_SCHEMA",
    "FRESHNESS_STATES",
    "GLOSSARY_ENTRY_SCHEMA",
    "GREEN_LIKE",
    "KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA",
    "KnowledgeAcquisitionError",
    "MEMORY_PROMOTION_REQUEST_SCHEMA",
    "MINI_TASK_AUDIT_SCHEMA",
    "MINI_TASK_SCHEMA",
    "SOURCE_ARTIFACT_SCHEMA",
    "SOURCE_CITATION_SCHEMA",
    "SOURCE_FRESHNESS_REVIEW_SCHEMA",
    "as_list",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "require_fields",
]
