"""Build the divergence matrix from normalized receipts.

Divergence is recorded *descriptively*. Model disagreement is never treated as
evidence by itself: every record carries `is_evidence: False`.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import (
    DIVERGENCE_MATRIX_SCHEMA,
    DIVERGENCE_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _by_prompt(receipts: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in receipts:
        grouped.setdefault(r["prompt_id"], []).append(r)
    return grouped


def _record(prompt_id: str, divergence_type: str, observations: dict, receipt_ids: list[str]) -> dict:
    rec = {
        "schema": DIVERGENCE_RECORD_SCHEMA,
        "prompt_id": prompt_id,
        "divergence_type": divergence_type,
        "observations": observations,
        "receipt_ids": sorted(receipt_ids),
        "is_evidence": False,
        "is_truth": False,
        **neutral_flags(),
    }
    rec["record_hash"] = canonical_hash(rec)
    return rec


def _distinct(values: list) -> bool:
    return len({tuple(v) if isinstance(v, list) else v for v in values}) > 1


def build_divergence_matrix(receipts: list[dict]) -> dict:
    records: list[dict] = []
    for prompt_id, group in sorted(_by_prompt(receipts).items()):
        if len(group) < 2:
            continue
        rids = [r["receipt_id"] for r in group]

        claim_sets = {r["participant_id"]: r["included_claim_tags"] for r in group}
        if _distinct(list(claim_sets.values())):
            records.append(_record(prompt_id, "factual_claim_divergence", claim_sets, rids))

        framings = {r["participant_id"]: r["framing_tags"] for r in group}
        if _distinct(list(framings.values())):
            records.append(_record(prompt_id, "framing_divergence", framings, rids))

        refusals = {r["participant_id"]: r["refusal_state"] for r in group}
        if _distinct(list(refusals.values())):
            records.append(_record(prompt_id, "refusal_divergence", refusals, rids))

        moral = {r["participant_id"]: r["moral_principle_tags"] for r in group}
        if _distinct(list(moral.values())):
            records.append(_record(prompt_id, "moral_framing_divergence", moral, rids))

        gaps = {r["participant_id"]: bool(r["evidence_gap_tags"]) for r in group}
        if _distinct(list(gaps.values())):
            records.append(_record(prompt_id, "evidence_gap_divergence", gaps, rids))

        sourced = {r["participant_id"]: r["sourced"] for r in group}
        if _distinct(list(sourced.values())):
            records.append(_record(prompt_id, "omission_divergence", sourced, rids))

    matrix = {
        "schema": DIVERGENCE_MATRIX_SCHEMA,
        "version": "divergence_matrix_v1",
        "records": records,
        "record_count": len(records),
        "divergence_is_not_evidence": True,
        "divergence_is_truth": False,
        **neutral_flags(),
    }
    matrix["matrix_hash"] = canonical_hash(matrix)
    return matrix
