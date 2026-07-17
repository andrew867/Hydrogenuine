"""Map P26 memory sources to P27 skill records."""

from __future__ import annotations

from hg_runtime.skill_graph.skill_extractor import extract_skills_from_p26


def map_skill_sources(repo_root) -> dict:
    return extract_skills_from_p26(repo_root)
