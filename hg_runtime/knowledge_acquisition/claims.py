"""Claim records.

Unsupported claims default to TBD. A claim can only carry a "green/supported"
status when it is both evidence-linked and source-linked. Single-source claims
are limited scope. Contradictions are flagged, never silently reconciled.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    CLAIM_RECORD_SCHEMA,
    GREEN_LIKE,
    KnowledgeAcquisitionError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)

TBD = "tbd"


def create_claim_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("claim_id", "statement", "evidence_refs", "source_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    evidence = as_list(data, "evidence_refs")
    sources = as_list(data, "source_refs")
    desired = str(data.get("status", TBD)).lower()
    enforce = bool(data.get("enforce_status"))

    if not evidence:
        # No evidence -> the claim is unsupported and is marked TBD. Quietly
        # demanding a green status over no evidence is a fake-green attempt.
        if enforce and desired in GREEN_LIKE:
            raise KnowledgeAcquisitionError("fake_green_rejected:unsupported_claim_cannot_be_green")
        data["status"] = TBD
        data["supported"] = False
    else:
        # Evidence present -> a green-like claim still needs a source link.
        if desired in GREEN_LIKE and not sources:
            raise KnowledgeAcquisitionError("source_claim_link_required")
        data["status"] = desired if desired != TBD else "candidate"
        data["supported"] = bool(sources)

    # Single-source support is real but bounded; record the limited scope.
    if len(sources) <= 1:
        data["scope"] = "limited_single_source" if sources else "unsourced"
        data["single_source"] = bool(sources)
    else:
        data.setdefault("scope", "multi_source")
        data["single_source"] = False

    data.setdefault("schema", CLAIM_RECORD_SCHEMA)
    data.update(neutral_flags())
    return data


def detect_contradictions(claims: Iterable[Mapping[str, Any]]) -> list[str]:
    """Flag claim ids that assert opposite polarity about the same subject."""
    by_subject: dict[str, dict[str, set[str]]] = {}
    for claim in claims:
        subject = claim.get("subject")
        if subject is None:
            continue
        polarity = bool(claim.get("polarity", True))
        bucket = by_subject.setdefault(subject, {True: set(), False: set()})  # type: ignore[index]
        bucket[polarity].add(str(claim.get("claim_id")))
    flagged: set[str] = set()
    for bucket in by_subject.values():
        if bucket[True] and bucket[False]:
            flagged |= bucket[True] | bucket[False]
    return sorted(flagged)


__all__ = ["TBD", "create_claim_record", "detect_contradictions"]
