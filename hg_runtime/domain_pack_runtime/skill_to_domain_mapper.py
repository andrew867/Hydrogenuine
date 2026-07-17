"""Map P27 skills to domain labels."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import assert_neutral


def map_skill_to_domain(skill: dict) -> dict:
    mapping = {
        "record_type": "skill_to_domain_mapping_v1",
        "schema_version": "1",
        "skill_id": skill["skill_id"],
        "domain_label": skill["domain_hint"],
        "procedure_tag": skill["procedure_tag"],
        "boundary_tags": list(skill["boundary_tags"]),
        "provenance_refs": list(skill["provenance_refs"]),
        "domain_label_is_not_expertise": True,
        "skill_link_is_not_authority": True,
    }
    with_hash(mapping, "record_hash")
    assert_neutral(mapping)
    return mapping


def map_skills_to_domains(skills: list[dict]) -> list[dict]:
    return [map_skill_to_domain(skill) for skill in skills]


def group_skills_by_domain(skills: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for skill in skills:
        grouped.setdefault(skill["domain_hint"], []).append(skill)
    return grouped
