"""Extract moral principle overlap and conflict descriptively.

Shared moral framing is recorded as descriptive overlap, never as moral
authority. Conflicts are recorded without adjudication.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import (
    MORAL_CONFLICT_RECORD_SCHEMA,
    MORAL_CONSENSUS_MATRIX_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_moral_consensus_matrix(receipts: list[dict]) -> dict:
    tag_participants: dict[str, set[str]] = {}
    for r in receipts:
        for tag in r["moral_principle_tags"]:
            tag_participants.setdefault(tag, set()).add(r["participant_id"])
    overlaps = [
        {
            "principle_tag": tag,
            "participant_ids": sorted(parts),
            "participant_count": len(parts),
            "is_shared": len(parts) > 1,
        }
        for tag, parts in sorted(tag_participants.items())
    ]
    matrix = {
        "schema": MORAL_CONSENSUS_MATRIX_SCHEMA,
        "version": "moral_consensus_matrix_v1",
        "principle_overlaps": overlaps,
        "principle_count": len(overlaps),
        "shared_principle_count": sum(1 for o in overlaps if o["is_shared"]),
        "moral_consensus_is_authority": False,
        "moral_consensus_treated_as_authority": False,
        "moral_consensus_is_truth": False,
        **neutral_flags(),
    }
    matrix["matrix_hash"] = canonical_hash(matrix)
    return matrix


def extract_moral_conflicts(receipts: list[dict]) -> list[dict]:
    by_axis: dict[tuple[str, str], dict[str, str]] = {}
    for r in receipts:
        axis = r.get("moral_conflict_axis")
        stance = r.get("moral_stance")
        if not axis or not stance:
            continue
        by_axis.setdefault((r["prompt_id"], axis), {})[r["participant_id"]] = stance

    records: list[dict] = []
    for (prompt_id, axis), stances in sorted(by_axis.items()):
        if len(set(stances.values())) < 2:
            continue
        record = {
            "schema": MORAL_CONFLICT_RECORD_SCHEMA,
            "prompt_id": prompt_id,
            "conflict_axis": axis,
            "stances": dict(sorted(stances.items())),
            "adjudicated": False,
            "resolution": "none_recorded_no_adjudication",
            "moral_claim_treated_as_authority": False,
            "is_evidence": False,
            **neutral_flags(),
        }
        record["record_hash"] = canonical_hash(record)
        records.append(record)
    return records
