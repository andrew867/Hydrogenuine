"""P27 skill record builders."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import assert_neutral, neutral_flags


def build_skill_record(
    *,
    skill_id: str,
    skill_name: str,
    procedure_tag: str,
    domain_hint: str,
    boundary_tags: list[str],
    memory_id: str,
    memory_hash: str,
    provenance_refs: list[str],
    source_quality_refs: list[str] | None = None,
    confidence_descriptive: float = 0.5,
) -> dict:
    record = {
        "record_type": "skill_record_v1",
        "schema_version": "1",
        "skill_id": skill_id,
        "skill_name": skill_name,
        "procedure_tag": procedure_tag,
        "domain_hint": domain_hint,
        "boundary_tags": list(boundary_tags),
        "memory_id": memory_id,
        "memory_hash": memory_hash,
        "provenance_refs": list(provenance_refs),
        "source_quality_refs": list(source_quality_refs or []),
        "confidence_descriptive": confidence_descriptive,
        "confidence_is_not_competence": True,
        "skill_is_not_authority": True,
        "skill_reuse_is_not_transfer_proof": True,
        "doctrine_note": "Skill is not authority; confidence is descriptive only.",
        **neutral_flags(),
    }
    with_hash(record, "skill_hash")
    assert_neutral(record)
    return record
