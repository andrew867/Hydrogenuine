"""Detect belief conflicts from WMBR-01A matrix artifacts.

A belief-conflict record describes claim-level tension WITHOUT resolving truth.
`truth_resolved` is always False. A conflict record is not evidence.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    BELIEF_CONFLICT_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

# Map WMBR-01A divergence_type -> WMBR-02 conflict_type.
DIVERGENCE_TO_CONFLICT = {
    "factual_claim_divergence": "FACTUAL_DIVERGENCE",
    "framing_divergence": "FRAMING_DIVERGENCE",
    "refusal_divergence": "REFUSAL_DIVERGENCE",
    "omission_divergence": "OMISSION_DIVERGENCE",
    "moral_framing_divergence": "MORAL_CONFLICT",
}


def _record(conflict_type: str, source_matrix_id: str, receipt_ids: list[str], claim_ref: str, requires_verification: bool, note: str) -> dict:
    rec = {
        "schema": BELIEF_CONFLICT_RECORD_SCHEMA,
        "conflict_id": f"conflict-{conflict_type.lower()}-{canonical_hash({'m': source_matrix_id, 'r': sorted(receipt_ids), 'c': claim_ref})[:16]}",
        "source_matrix_id": source_matrix_id,
        "source_receipt_ids": sorted(receipt_ids),
        "claim_text_or_hash": claim_ref,
        "conflict_type": conflict_type,
        "note": note,
        "truth_resolved": False,
        "evidence_present": False,
        "requires_verification": requires_verification,
        "conflict_record_treated_as_evidence": False,
        **neutral_flags(),
    }
    rec["record_hash"] = canonical_hash(rec)
    return rec


def detect_conflicts(bundle: dict) -> list[dict]:
    pm_id = bundle["perspective_matrix"].get("matrix_hash", "perspective_matrix")
    dm = bundle["divergence_matrix"]
    records: list[dict] = []

    # 1. Divergence-derived conflicts.
    for rec in dm.get("records", []):
        conflict_type = DIVERGENCE_TO_CONFLICT.get(rec.get("divergence_type"))
        if not conflict_type:
            continue
        records.append(_record(
            conflict_type, pm_id, rec.get("receipt_ids", []),
            f"prompt:{rec.get('prompt_id')}", True,
            f"Derived from divergence_type={rec.get('divergence_type')}; descriptive only.",
        ))

    # 2. Moral conflict records.
    for rec in bundle.get("moral_conflict_records", []):
        records.append(_record(
            "MORAL_CONFLICT", pm_id, [], f"prompt:{rec.get('prompt_id')}|axis:{rec.get('conflict_axis')}", True,
            "Derived from moral_conflict_record; no moral adjudication.",
        ))

    # 3. Unsourced consensus, from WMBR-01A evidence_gap_tasks of that kind.
    for task in bundle.get("evidence_gap_tasks", []):
        if task.get("task_kind") == "unsourced_consensus":
            records.append(_record(
                "UNSOURCED_CONSENSUS", pm_id, task.get("receipt_ids", []),
                f"claim_tag:{task.get('claim_tag')}", True,
                "Multiple models share a claim with no sources; consensus is not truth.",
            ))

    # Deterministic order, de-duplicated by conflict_id.
    seen: set[str] = set()
    deduped: list[dict] = []
    for rec in sorted(records, key=lambda r: (r["conflict_type"], r["conflict_id"])):
        if rec["conflict_id"] in seen:
            continue
        seen.add(rec["conflict_id"])
        deduped.append(rec)
    return deduped
