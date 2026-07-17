from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_gateway.tool_registry import (
    get_tool_registry_entry,
    get_tool_registry_summary,
    list_tool_inventory,
    list_tool_versions,
    sync_tool_registry,
)


def get_executable_registry_overview() -> dict[str, Any]:
    with get_connection() as conn:
        summary = get_tool_registry_summary(conn)
        tools = list_tool_inventory(conn)
    return {"summary": summary, "executables": tools}


def get_executable_registry_record(tool_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_tool_registry_entry(conn, tool_id)


def get_executable_registry_record_versions(tool_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_tool_versions(conn, tool_id)


def sync_executable_registry_service(root: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        return sync_tool_registry(conn, root=None if root is None else Path(root))
