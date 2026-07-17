"""Extract bounded skill candidates from P26 experience ledger."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.recall_index import build_recall_index
from hg_runtime.skill_graph.hashing import with_hash
from hg_runtime.skill_graph.p27_schemas import SkillGraphBatchBoundaryError, assert_neutral
from hg_runtime.skill_graph.skill_record import build_skill_record
from hg_runtime.skill_graph.transfer_record import build_skill_source_memory_link


def _procedure_tag(entry: dict) -> str:
    tags = entry.get("boundary_tags") or []
    if tags:
        return tags[0]
    return f"review_{entry['family'].lower().replace('-', '_')}"


def _skill_name(procedure_tag: str) -> str:
    return procedure_tag.replace("_", " ")


def build_p26_memory_manifest(repo_root: Path) -> dict:
    recall = build_recall_index(repo_root)
    manifest = {
        "record_type": "p27_p26_memory_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p27-1-p26-memory-manifest",
        "explicit_manifest_only": True,
        "memory_record_count": len(recall["memory_records"]),
        "recall_index_id": recall["index"]["index_id"],
        "recall_index_hash": recall["index"]["manifest_hash"],
        "memory_ids": [row["memory_id"] for row in recall["memory_records"]],
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {"manifest": manifest, "recall_index": recall}


def extract_skills_from_p26(repo_root: Path) -> dict:
    layer = build_p26_memory_manifest(repo_root)
    recall = layer["recall_index"]
    skills = []
    links = []
    rejections = []
    for i, entry in enumerate(recall["entries"], start=1):
        if not entry.get("provenance_refs"):
            rejections.append({"memory_id": entry["memory_id"], "reason": "missing_provenance"})
            continue
        skill = build_skill_record(
            skill_id=f"skill-{entry['memory_id'].removeprefix('mem-')}",
            skill_name=_skill_name(_procedure_tag(entry)),
            procedure_tag=_procedure_tag(entry),
            domain_hint=entry["family"],
            boundary_tags=list(entry["boundary_tags"]),
            memory_id=entry["memory_id"],
            memory_hash=entry["memory_hash"],
            provenance_refs=list(entry["provenance_refs"]),
            source_quality_refs=list(entry.get("source_quality_refs") or []),
            confidence_descriptive=0.4 + (0.1 * (i % 3)),
        )
        link = build_skill_source_memory_link(
            link_id=f"link-{skill['skill_id']}",
            skill_id=skill["skill_id"],
            memory_id=entry["memory_id"],
            memory_hash=entry["memory_hash"],
        )
        skills.append(skill)
        links.append(link)
    if not skills:
        raise SkillGraphBatchBoundaryError("no_skills_extracted")
    return {
        **layer,
        "skill_records": skills,
        "skill_source_memory_links": links,
        "skill_extraction_rejections": rejections,
    }
