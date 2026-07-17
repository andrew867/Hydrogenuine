"""Build domain capability maps from skill graph."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import assert_neutral
from hg_runtime.domain_pack_runtime.skill_to_domain_mapper import group_skills_by_domain


def build_domain_capability_map(skills: list[dict]) -> dict:
    grouped = group_skills_by_domain(skills)
    capabilities = []
    for domain_label, domain_skills in sorted(grouped.items()):
        capability = {
            "record_type": "domain_capability_v1",
            "schema_version": "1",
            "capability_id": f"cap-{domain_label.lower().replace('-', '_')}",
            "domain_label": domain_label,
            "procedure_tags": sorted({row["procedure_tag"] for row in domain_skills}),
            "skill_ids": [row["skill_id"] for row in domain_skills],
            "boundary_tags": sorted({tag for row in domain_skills for tag in row["boundary_tags"]}),
            "domain_label_is_not_expertise": True,
            "domain_pack_is_not_permission": True,
        }
        with_hash(capability, "record_hash")
        assert_neutral(capability)
        capabilities.append(capability)
    map_record = {
        "record_type": "domain_capability_map_v1",
        "schema_version": "1",
        "map_id": "p28-domain-capability-map",
        "domain_count": len(capabilities),
        "capabilities": capabilities,
        "domain_label_is_not_expertise": True,
    }
    with_hash(map_record, "capability_map_hash")
    assert_neutral(map_record)
    return map_record
