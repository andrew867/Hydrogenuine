"""Human-review and human-disagreement records.

Human review records a reviewer's verdict on a case. When reviewers disagree, the
disagreement is recorded explicitly and never hidden; an unresolved disagreement
prevents an unqualified GREEN for that case.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    HUMAN_DISAGREEMENT_RECORD_SCHEMA,
    HUMAN_REVIEW_RECORD_SCHEMA,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def record_human_review(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "reviewer", "verdict"))
    reject_authority_payload(payload)
    disagreements = list(payload.get("disagreements", []))
    review = {
        "schema": HUMAN_REVIEW_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "reviewer": payload["reviewer"],
        "verdict": payload["verdict"],
        "notes": payload.get("notes", ""),
        "disagreements": disagreements,
        "disagreement_unresolved": bool(payload.get("disagreement_unresolved", bool(disagreements) and not payload.get("resolved", False))),
        "advisory_only": True,
        **neutral_flags(),
    }
    review["record_hash"] = canonical_hash(review)
    return review


def record_human_disagreement(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "reviewer_a", "reviewer_b"))
    reject_authority_payload(payload)
    record = {
        "schema": HUMAN_DISAGREEMENT_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "reviewer_a": payload["reviewer_a"],
        "reviewer_b": payload["reviewer_b"],
        "verdict_a": payload.get("verdict_a", ""),
        "verdict_b": payload.get("verdict_b", ""),
        "summary": payload.get("summary", ""),
        "resolved": bool(payload.get("resolved", False)),
        "hidden": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


__all__ = ["record_human_disagreement", "record_human_review"]
