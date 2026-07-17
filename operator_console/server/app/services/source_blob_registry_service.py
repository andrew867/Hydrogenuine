from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_gateway.source_blob_registry import (
    archive_source_blob_document,
    compare_source_blob_versions,
    create_source_blob_document,
    get_source_blob_document,
    get_source_blob_inventory_summary,
    list_source_blob_inventory,
    list_source_blob_versions,
    restore_source_blob_document,
    save_source_blob_document,
    sync_source_blob_inventory,
)
from hg_core.source_blob_execution import run_source_blob_module


def get_source_blob_registry_overview() -> dict[str, Any]:
    with get_connection() as conn:
        summary = get_source_blob_inventory_summary(conn)
        blobs = list_source_blob_inventory(conn)
    return {"summary": summary, "source_blobs": blobs}


def get_source_blob_registry_record(source_blob_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_source_blob_document(conn, source_blob_id)


def get_source_blob_registry_record_versions(source_blob_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_source_blob_versions(conn, source_blob_id)


def sync_source_blob_registry_service(root: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        return sync_source_blob_inventory(conn, root=None if root is None else Path(root))


def create_source_blob_registry_record(
    class_key: str,
    file_path: str,
    source_text: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return create_source_blob_document(
            conn,
            class_key,
            file_path,
            source_text,
            title=title,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def save_source_blob_registry_record(
    source_blob_id: str,
    source_text: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return save_source_blob_document(
            conn,
            source_blob_id,
            source_text,
            title=title,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def archive_source_blob_registry_record(
    source_blob_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return archive_source_blob_document(
            conn,
            source_blob_id,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def restore_source_blob_registry_record(
    source_blob_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return restore_source_blob_document(
            conn,
            source_blob_id,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def compare_source_blob_registry_versions(
    source_blob_id: str,
    left_version_id: str | None = None,
    right_version_id: str | None = None,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        return compare_source_blob_versions(conn, source_blob_id, left_version_id, right_version_id)


def run_source_blob_registry_record(
    source_blob_id: str,
    *,
    entrypoint: str | None = None,
    args: list[str] | None = None,
    timeout_s: int = 120,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    return run_source_blob_module(
        source_blob_id,
        entrypoint=entrypoint,
        args=args,
        timeout_s=timeout_s,
        actor_id=actor_id,
        change_summary=change_summary,
    )
