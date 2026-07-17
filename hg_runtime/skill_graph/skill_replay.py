"""Replay P27 skill extraction deterministically."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.hashing import stable_hash
from hg_runtime.skill_graph.skill_extractor import extract_skills_from_p26


def replay_skill_extraction(repo_root: Path) -> dict:
    first = extract_skills_from_p26(repo_root)
    second = extract_skills_from_p26(repo_root)
    first_hash = stable_hash(
        {
            "skills": [row["skill_hash"] for row in first["skill_records"]],
            "links": [row["link_hash"] for row in first["skill_source_memory_links"]],
            "manifest": first["manifest"]["manifest_hash"],
        }
    )
    second_hash = stable_hash(
        {
            "skills": [row["skill_hash"] for row in second["skill_records"]],
            "links": [row["link_hash"] for row in second["skill_source_memory_links"]],
            "manifest": second["manifest"]["manifest_hash"],
        }
    )
    return {
        "replay_deterministic": first_hash == second_hash,
        "stable_hash": first_hash,
        "skill_count": len(first["skill_records"]),
    }
