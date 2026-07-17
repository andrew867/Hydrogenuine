from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_gateway.artifact_registry import (
    get_artifact_inventory_summary,
    get_artifact_registry_entry,
    inventory_artifacts,
    list_artifact_inventory,
    list_artifact_versions,
    sync_artifact_registry,
)
from hg_gateway.db import get_connection


def get_artifact_registry_overview() -> dict[str, Any]:
    with get_connection() as conn:
        summary = get_artifact_inventory_summary(conn)
        artifacts = list_artifact_inventory(conn)
    return {"summary": summary, "artifacts": artifacts}


def get_artifact_registry_record(artifact_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_artifact_registry_entry(conn, artifact_id)


def get_artifact_registry_record_versions(artifact_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_artifact_versions(conn, artifact_id)


def sync_artifact_registry_service(root: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        return sync_artifact_registry(conn, root=None if root is None else Path(root))
