"""Synthetic evidence receipts (test mechanics only).

Evidence receipts in this phase are SYNTHETIC and provenance-bound. They exist
to exercise belief-revision mechanics, not to assert real-world truth. A model
output is not evidence and a verification task is not evidence: receipts derived
from those sources are rejected. Every evidence receipt must carry provenance.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    BeliefRevisionError,
    EVIDENCE_KINDS,
    EVIDENCE_RECEIPT_SCHEMA,
    PROVENANCE_KINDS,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

TASK_TYPE_TO_EVIDENCE_KIND = {
    "PRIMARY_SOURCE_REQUEST": "SYNTHETIC_PRIMARY_SOURCE",
    "SOURCE_CHECK": "SYNTHETIC_SECONDARY_SOURCE",
    "CROSS_REFERENCE_REQUEST": "SYNTHETIC_SECONDARY_SOURCE",
    "POLICY_CONTEXT_CHECK": "SYNTHETIC_POLICY_CONTEXT",
    "DEFINITIONS_REQUEST": "SYNTHETIC_SECONDARY_SOURCE",
    "TIMELINE_CHECK": "SYNTHETIC_TIMELINE_CHECK",
    "NUMERIC_CHECK": "SYNTHETIC_NUMERIC_CHECK",
}


def build_synthetic_evidence_receipt(
    *,
    task: dict,
    target_claim_id: str,
    stance: str,
    ordinal: int,
) -> dict:
    """Build a deterministic synthetic evidence receipt.

    stance: "SUPPORTS", "CONTRADICTS", or "INSUFFICIENT".
    """
    if stance not in ("SUPPORTS", "CONTRADICTS", "INSUFFICIENT"):
        raise BeliefRevisionError("invalid_stance")
    task_id = task.get("task_id", "task-unknown")
    task_type = task.get("task_type", "SOURCE_CHECK")
    evidence_kind = TASK_TYPE_TO_EVIDENCE_KIND.get(task_type, "SYNTHETIC_SECONDARY_SOURCE")
    supports = [target_claim_id] if stance == "SUPPORTS" else []
    contradicts = [target_claim_id] if stance == "CONTRADICTS" else []
    fixture_id = f"fixture-evidence-{task_id}-{stance.lower()}-{ordinal}"
    text = f"[synthetic {stance.lower()} evidence for {target_claim_id} via {evidence_kind}]"
    receipt = {
        "schema": EVIDENCE_RECEIPT_SCHEMA,
        "evidence_receipt_id": f"ev-{task_id}-{stance.lower()}-{ordinal}",
        "source_task_id": task_id,
        "source_claim_ids": sorted(set([target_claim_id, *task.get("source_claim_ids", [])])),
        "evidence_kind": evidence_kind,
        "stance": stance,
        "evidence_text_hash": canonical_hash({"text": text}),
        "evidence_text_redacted": text,
        "provenance_uri_or_fixture_id": fixture_id,
        "provenance_kind": "FIXTURE",
        "supports_claim_ids": supports,
        "contradicts_claim_ids": contradicts,
        "uncertainty_notes": "Synthetic fixture evidence; FUTURE_EXTERNAL_SOURCE_REQUIRED for any real claim.",
        "model_output_is_evidence": False,
        "external_call_made": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def validate_evidence_receipt(receipt: dict) -> None:
    """Reject receipts that lack provenance or launder a forbidden evidence source."""
    if receipt.get("evidence_kind") not in EVIDENCE_KINDS:
        raise BeliefRevisionError("invalid_evidence_kind")
    if not receipt.get("provenance_uri_or_fixture_id"):
        raise BeliefRevisionError("evidence_receipt_missing_provenance")
    if receipt.get("provenance_kind") not in PROVENANCE_KINDS:
        raise BeliefRevisionError("evidence_receipt_missing_provenance")
    if receipt.get("model_output_is_evidence") or receipt.get("model_output_treated_as_evidence"):
        raise BeliefRevisionError("model_output_treated_as_evidence")
    if receipt.get("model_consensus_treated_as_evidence"):
        raise BeliefRevisionError("model_consensus_treated_as_evidence")
    if receipt.get("verification_task_treated_as_evidence"):
        raise BeliefRevisionError("verification_task_treated_as_evidence")
    if receipt.get("evidence_kind") == "VERIFICATION_TASK":
        raise BeliefRevisionError("verification_task_treated_as_evidence")
