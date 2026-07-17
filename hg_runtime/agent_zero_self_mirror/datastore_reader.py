"""Data store metadata reflection — no private content dumps."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_zero_self_mirror.repo_index import WORKSPACE
from hg_runtime.agent_zero_self_mirror.schema import DataStoreIndex, IndexStatus

STORAGE_CONFIG_HINTS = [
    WORKSPACE / "configs" / "storage",
    WORKSPACE / "config" / "schema_registry.yaml",
    WORKSPACE / "config" / "truth_gate_registry.yaml",
]


def build_datastore_index() -> DataStoreIndex:
    stores: list[dict] = []
    # Metadata from config/registry references — not live secret values
    stores.append({
        "store_name": "storage_artifact_vector",
        "schema_version": "storage/1",
        "status": "governed",
        "retention_class": "proof-backed",
        "content_policy": "metadata_only_in_self_mirror",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    })
    stores.append({
        "store_name": "memory_tool_contracts",
        "schema_version": "memory/1",
        "status": "governed_via_broker",
        "content_policy": "no_private_dump_in_self_mirror",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    })
    for hint in STORAGE_CONFIG_HINTS:
        if hint.is_file():
            stores.append({
                "store_name": hint.name,
                "config_path": str(hint.relative_to(WORKSPACE)).replace("\\", "/"),
                "status": "config_reference",
                "advisory_only": True,
                "permission_granted": False,
                "authority_created": False,
            })
        elif hint.is_dir():
            for f in hint.glob("*.json"):
                rel = str(f.relative_to(WORKSPACE)).replace("\\", "/")
                if ".env" in rel.lower():
                    continue
                stores.append({
                    "store_name": f.stem,
                    "config_path": rel,
                    "status": "config_reference",
                    "advisory_only": True,
                    "permission_granted": False,
                    "authority_created": False,
                })
    return DataStoreIndex(status=IndexStatus.READY, stores=stores)


__all__ = ["build_datastore_index"]
