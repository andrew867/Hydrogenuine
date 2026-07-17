"""Memory promotion and advisory hand-offs.

Promotion is the only path by which acquired knowledge enters durable memory, and
it is gated: it requires citation refs and audit refs, refuses stale-source
promotion without review, and emits a genuine Phase 26 memory receipt. Skill and
domain-readiness hand-offs are advisory only.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.ledger import LedgerEntry, PersistentMemoryLedger
from hg_runtime.memory_ledger.schemas import MEMORY_EVENT_SCHEMA, OperationControl
from hg_runtime.knowledge_acquisition.schemas import (
    DOMAIN_READINESS_RECORD_SCHEMA,
    KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA,
    MEMORY_PROMOTION_REQUEST_SCHEMA,
    GREEN_LIKE,
    KnowledgeAcquisitionError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)

SKILL_CANDIDATE_SCHEMA = "acquisition_skill_candidate_v1"


def request_memory_promotion(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(
        payload,
        ("promotion_id", "target_memory", "claim_refs", "citation_refs", "audit_refs", "claim_boundary"),
    )
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    citation_refs = as_list(data, "citation_refs")
    audit_refs = as_list(data, "audit_refs")
    if not citation_refs or not audit_refs:
        raise KnowledgeAcquisitionError("memory_promotion_requires_citation_and_audit")

    # A stale source cannot be promoted unless its review is complete.
    for review in as_list(data, "source_reviews"):
        if isinstance(review, Mapping):
            status = str(review.get("status", "")).lower()
            if status in {"stale", "needs_review"} and not review.get("review_completed"):
                raise KnowledgeAcquisitionError("stale_source_cannot_promote_without_review")

    data.setdefault("schema", MEMORY_PROMOTION_REQUEST_SCHEMA)
    data.update(neutral_flags())
    return data


def build_acquisition_outcome_receipt(
    *,
    status: str,
    receipt_refs: list[str],
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A success/green acquisition outcome cannot be recorded without receipts."""
    if str(status).lower() in GREEN_LIKE and not receipt_refs:
        raise KnowledgeAcquisitionError("missing_receipt_blocks_success")
    receipt = {
        "schema": KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA,
        "status": status,
        "receipt_refs": list(receipt_refs),
        "summary": dict(summary or {}),
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def promote_to_memory(
    ledger: PersistentMemoryLedger,
    request: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
    created_at: str | None = None,
) -> tuple[LedgerEntry, dict[str, Any]]:
    """Promote audited, cited knowledge into the Phase 26 ledger.

    Returns the appended Phase 26 ledger entry and a knowledge-acquisition
    receipt that binds to it. The Phase 26 ``PROMOTION`` event itself refuses to
    append without receipt refs, so a citationless/auditless promotion can never
    succeed.
    """
    preempt_if_needed(control, stop_blocks=True)
    req = request_memory_promotion(request)
    receipt_refs = list(req["citation_refs"]) + list(req["audit_refs"])
    provenance = as_list(req, "source_refs") or list(req["citation_refs"])

    event = {
        "event_type": "PROMOTION",
        "subject": req["target_memory"],
        "scope": req.get("scope", "acquired_knowledge"),
        "claim": req.get("claim", "promoted audited, cited acquired knowledge"),
        "provenance_refs": provenance,
        "authority_refs": ["gpp:reference-only"],
        "receipt_refs": receipt_refs,
        "confidence": req.get("confidence", "evidence_bound"),
        "status": "active",
        "claim_boundary": "evidence_only",
    }
    entry = ledger.append_memory_event(event, created_at=created_at)

    receipt = {
        "schema": KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA,
        "promotion_id": req["promotion_id"],
        "phase26_schema": MEMORY_EVENT_SCHEMA,
        "memory_entry_id": entry.entry_id,
        "memory_chain_hash": entry.chain_hash,
        "citation_refs": req["citation_refs"],
        "audit_refs": req["audit_refs"],
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return entry, receipt


def build_skill_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Advisory hand-off to Phase 27. A skill candidate never authorizes a tool."""
    require_fields(payload, ("candidate_id", "procedure", "evidence_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    data.setdefault("schema", SKILL_CANDIDATE_SCHEMA)
    data["advisory_only"] = True
    data.update(neutral_flags())
    return data


def build_domain_readiness_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Advisory hand-off to Phase 34. Readiness is evidence, not a green light."""
    require_fields(payload, ("domain", "readiness", "evidence_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    data.setdefault("schema", DOMAIN_READINESS_RECORD_SCHEMA)
    data["advisory_only"] = True
    data.update(neutral_flags())
    return data


__all__ = [
    "SKILL_CANDIDATE_SCHEMA",
    "build_acquisition_outcome_receipt",
    "build_domain_readiness_record",
    "build_skill_candidate",
    "promote_to_memory",
    "request_memory_promotion",
]
