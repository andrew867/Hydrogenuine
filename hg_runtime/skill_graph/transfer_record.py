"""P27 transfer record builders."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import assert_neutral, neutral_flags


def build_skill_source_memory_link(*, link_id: str, skill_id: str, memory_id: str, memory_hash: str) -> dict:
    record = {
        "record_type": "skill_source_memory_link_v1",
        "schema_version": "1",
        "link_id": link_id,
        "skill_id": skill_id,
        "memory_id": memory_id,
        "memory_hash": memory_hash,
        "memory_source_required": True,
        **neutral_flags(),
    }
    with_hash(record, "link_hash")
    assert_neutral(record)
    return record


def build_transfer_candidate(
    *,
    candidate_id: str,
    source_skill_id: str,
    target_skill_id: str,
    source_domain: str,
    target_domain: str,
    link_reason: str,
    evidence_refs: list[str],
    provenance_refs: list[str],
    negative_transfer_risk: str = "medium",
) -> dict:
    record = {
        "record_type": "transfer_candidate_v1",
        "schema_version": "1",
        "candidate_id": candidate_id,
        "source_skill_id": source_skill_id,
        "target_skill_id": target_skill_id,
        "source_domain": source_domain,
        "target_domain": target_domain,
        "link_reason": link_reason,
        "evidence_refs": list(evidence_refs),
        "provenance_refs": list(provenance_refs),
        "negative_transfer_risk": negative_transfer_risk,
        "status": "hypothesis",
        "transfer_candidate_is_not_competence": True,
        "transfer_is_not_proof": True,
        **neutral_flags(),
    }
    with_hash(record, "transfer_hash")
    assert_neutral(record)
    return record


def build_transfer_result(
    *,
    result_id: str,
    candidate_id: str,
    outcome: str,
    mismatch_detected: bool = False,
) -> dict:
    record = {
        "record_type": "transfer_result_v1",
        "schema_version": "1",
        "result_id": result_id,
        "candidate_id": candidate_id,
        "outcome": outcome,
        "mismatch_detected": mismatch_detected,
        "transfer_is_not_proof": True,
        "mutation_auto_repaired": False,
        **neutral_flags(),
    }
    with_hash(record, "record_hash")
    assert_neutral(record)
    return record
