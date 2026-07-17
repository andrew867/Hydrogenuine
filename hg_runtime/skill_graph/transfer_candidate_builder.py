"""Build transfer candidates from skill graph."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import assert_neutral
from hg_runtime.skill_graph.skill_graph_index import build_skill_graph_edges, build_skill_graph_index
from hg_runtime.skill_graph.transfer_record import build_transfer_candidate


def build_transfer_candidates(repo_root) -> dict:
    layer = build_skill_graph_index(repo_root)
    skills = layer["skill_records"]
    edges = build_skill_graph_edges(skills)
    candidates = []
    for i, edge in enumerate(edges, start=1):
        source = next(row for row in skills if row["skill_id"] == edge["source_skill_id"])
        target = next(row for row in skills if row["skill_id"] == edge["target_skill_id"])
        candidates.append(
            build_transfer_candidate(
                candidate_id=f"transfer-{i:03d}",
                source_skill_id=source["skill_id"],
                target_skill_id=target["skill_id"],
                source_domain=source["domain_hint"],
                target_domain=target["domain_hint"],
                link_reason=edge["edge_type"],
                evidence_refs=list(edge["evidence_refs"]),
                provenance_refs=sorted(set(source["provenance_refs"]) | set(target["provenance_refs"])),
                negative_transfer_risk="medium" if source["domain_hint"] != target["domain_hint"] else "low",
            )
        )
    manifest = {
        "record_type": "transfer_candidate_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p27-2-transfer-candidates",
        "candidate_count": len(candidates),
        "edge_count": len(edges),
        "transfer_is_not_proof": True,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {
        **layer,
        "skill_edges": edges,
        "transfer_candidates": candidates,
        "transfer_candidate_manifest": manifest,
    }
