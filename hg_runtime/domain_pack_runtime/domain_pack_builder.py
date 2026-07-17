"""Build domain packs from P27 skill graph manifest."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_capability_map import build_domain_capability_map
from hg_runtime.domain_pack_runtime.domain_pack_policy import build_domain_pack_policy
from hg_runtime.domain_pack_runtime.domain_pack_record import (
    build_domain_pack_boundary_record,
    build_domain_pack_record,
    build_domain_pack_skill_link,
)
from hg_runtime.domain_pack_runtime.hashing import with_hash
from hg_runtime.domain_pack_runtime.schemas import assert_neutral
from hg_runtime.domain_pack_runtime.skill_to_domain_mapper import group_skills_by_domain
from hg_runtime.skill_graph.transfer_candidate_builder import build_transfer_candidates


def build_p27_skill_graph_manifest(repo_root: Path) -> dict:
    layer = build_transfer_candidates(repo_root)
    manifest = {
        "record_type": "p28_p27_skill_graph_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p28-1-p27-skill-graph-manifest",
        "explicit_manifest_only": True,
        "skill_graph_index_hash": layer["skill_graph_index"]["manifest_hash"],
        "transfer_manifest_hash": layer["transfer_candidate_manifest"]["manifest_hash"],
        "skill_count": len(layer["skill_records"]),
        "transfer_candidate_count": len(layer["transfer_candidates"]),
        "skill_ids": [row["skill_id"] for row in layer["skill_records"]],
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {**layer, "p27_manifest": manifest}


def build_domain_packs(repo_root: Path) -> dict:
    layer = build_p27_skill_graph_manifest(repo_root)
    policy = build_domain_pack_policy()
    skills = layer["skill_records"]
    grouped = group_skills_by_domain(skills)
    packs = []
    links = []
    boundaries = []
    for domain_label, domain_skills in sorted(grouped.items()):
        pack_id = f"pack-{domain_label.lower().replace('-', '_')}"
        provenance = sorted({ref for row in domain_skills for ref in row["provenance_refs"]})
        boundary_tags = sorted({tag for row in domain_skills for tag in row["boundary_tags"]})
        pack = build_domain_pack_record(
            pack_id=pack_id,
            domain_label=domain_label,
            skill_ids=[row["skill_id"] for row in domain_skills],
            provenance_refs=provenance,
            boundary_tags=boundary_tags,
            capability_refs=[f"cap-{domain_label.lower().replace('-', '_')}"],
        )
        packs.append(pack)
        for skill in domain_skills:
            links.append(
                build_domain_pack_skill_link(
                    link_id=f"link-{pack_id}-{skill['skill_id']}",
                    pack_id=pack_id,
                    skill_id=skill["skill_id"],
                    domain_label=domain_label,
                    provenance_refs=list(skill["provenance_refs"]),
                )
            )
        boundaries.append(
            build_domain_pack_boundary_record(
                boundary_id=f"boundary-{pack_id}",
                pack_id=pack_id,
                boundary_tags=boundary_tags,
            )
        )
    capability_map = build_domain_capability_map(skills)
    builder_manifest = {
        "record_type": "domain_pack_builder_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p28-1-domain-pack-builder",
        "pack_count": len(packs),
        "domain_pack_is_not_permission": True,
        "domain_label_is_not_expertise": True,
    }
    with_hash(builder_manifest, "manifest_hash")
    assert_neutral(builder_manifest)
    return {
        **layer,
        "policy": policy,
        "domain_packs": packs,
        "domain_pack_skill_links": links,
        "domain_pack_boundaries": boundaries,
        "capability_map": capability_map,
        "builder_manifest": builder_manifest,
    }
