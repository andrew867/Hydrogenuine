"""Replay domain pack building deterministically."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_pack_builder import build_domain_packs
from hg_runtime.domain_pack_runtime.hashing import stable_hash


def replay_domain_pack_build(repo_root: Path) -> dict:
    first = build_domain_packs(repo_root)
    second = build_domain_packs(repo_root)
    first_hash = stable_hash(
        {
            "packs": [row["pack_hash"] for row in first["domain_packs"]],
            "links": [row["link_hash"] for row in first["domain_pack_skill_links"]],
            "manifest": first["builder_manifest"]["manifest_hash"],
        }
    )
    second_hash = stable_hash(
        {
            "packs": [row["pack_hash"] for row in second["domain_packs"]],
            "links": [row["link_hash"] for row in second["domain_pack_skill_links"]],
            "manifest": second["builder_manifest"]["manifest_hash"],
        }
    )
    return {
        "replay_deterministic": first_hash == second_hash,
        "stable_hash": first_hash,
        "pack_count": len(first["domain_packs"]),
    }
