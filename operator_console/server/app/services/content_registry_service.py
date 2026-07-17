from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from hg_gateway.content_cms import (
    archive_content_document,
    create_content_document,
    get_content_document,
    get_content_inventory_summary,
    inventory_content,
    list_content_inventory,
    list_content_versions,
    restore_content_document,
    save_content_document,
    sync_content_inventory,
)
from hg_gateway.db import get_connection


def get_content_registry_overview() -> dict[str, Any]:
    with get_connection() as conn:
        summary = get_content_inventory_summary(conn)
        documents = list_content_inventory(conn)
    return {"summary": summary, "documents": documents}


def get_content_registry_document(content_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_content_document(conn, content_id)


def get_content_registry_versions(content_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_content_versions(conn, content_id)


def sync_content_registry(root: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        return sync_content_inventory(conn, root=None if root is None else Path(root))


def save_content_registry_document(
    content_id: str,
    content_markdown: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return save_content_document(
            conn,
            content_id,
            content_markdown,
            title=title,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def create_content_registry_document(
    class_key: str,
    file_path: str,
    content_markdown: str,
    *,
    title: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return create_content_document(
            conn,
            class_key,
            file_path,
            content_markdown,
            title=title,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def archive_content_registry_document(
    content_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return archive_content_document(conn, content_id, actor_id=actor_id, change_summary=change_summary)


def restore_content_registry_document(
    content_id: str,
    *,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return restore_content_document(conn, content_id, actor_id=actor_id, change_summary=change_summary)
