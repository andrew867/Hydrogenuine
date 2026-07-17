"""Build P27 skill graph index and edges."""

from __future__ import annotations

from hg_runtime.skill_graph.hashing import stable_hash, with_hash
from hg_runtime.skill_graph.p27_schemas import assert_neutral
from hg_runtime.skill_graph.skill_edge import build_skill_edge
from hg_runtime.skill_graph.skill_extractor import extract_skills_from_p26


def build_skill_graph_index(repo_root) -> dict:
    extraction = extract_skills_from_p26(repo_root)
    skills = extraction["skill_records"]
    index = {
        "record_type": "skill_graph_index_v1",
        "schema_version": "1",
        "index_id": "p27-2-skill-graph-index",
        "skill_count": len(skills),
        "skill_ids": [row["skill_id"] for row in skills],
        "domain_hints": sorted({row["domain_hint"] for row in skills}),
        "procedure_tags": sorted({row["procedure_tag"] for row in skills}),
    }
    with_hash(index, "manifest_hash")
    assert_neutral(index)
    return {**extraction, "skill_graph_index": index}


def build_skill_graph_edges(skills: list[dict]) -> list[dict]:
    edges = []
    for i, left in enumerate(skills):
        for j, right in enumerate(skills):
            if i >= j:
                continue
            shared_boundary = set(left["boundary_tags"]) & set(right["boundary_tags"])
            shared_provenance = set(left["provenance_refs"]) & set(right["provenance_refs"])
            shared_domain = left["domain_hint"] == right["domain_hint"]
            if shared_boundary:
                edges.append(
                    build_skill_edge(
                        edge_id=f"edge-boundary-{i:02d}-{j:02d}",
                        source_skill_id=left["skill_id"],
                        target_skill_id=right["skill_id"],
                        edge_type="shared_boundary_tag",
                        evidence_refs=sorted(shared_boundary),
                    )
                )
            elif shared_provenance:
                edges.append(
                    build_skill_edge(
                        edge_id=f"edge-provenance-{i:02d}-{j:02d}",
                        source_skill_id=left["skill_id"],
                        target_skill_id=right["skill_id"],
                        edge_type="shared_provenance_ref",
                        evidence_refs=sorted(shared_provenance),
                    )
                )
            elif shared_domain:
                edges.append(
                    build_skill_edge(
                        edge_id=f"edge-domain-{i:02d}-{j:02d}",
                        source_skill_id=left["skill_id"],
                        target_skill_id=right["skill_id"],
                        edge_type="shared_domain_hint",
                        evidence_refs=[left["domain_hint"]],
                    )
                )
    if not edges and len(skills) >= 2:
        left, right = skills[0], skills[1]
        edges.append(
            build_skill_edge(
                edge_id="edge-manifest-coherence-00-01",
                source_skill_id=left["skill_id"],
                target_skill_id=right["skill_id"],
                edge_type="explicit_manifest_coherence",
                evidence_refs=sorted(set(left["provenance_refs"]) & set(right["provenance_refs"]) or ["explicit_manifest_only"]),
            )
        )
    return edges
