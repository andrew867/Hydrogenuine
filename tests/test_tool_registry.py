from __future__ import annotations

from pathlib import Path
import json

from hg_gateway.db import get_connection
from hg_core.job_registry import get_job_info
from hg_gateway.tool_registry import (
    get_tool_registry_entry,
    get_tool_registry_summary,
    inventory_tool_registry,
    list_tool_inventory,
    sync_tool_registry,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_tool_registry_inventory_and_round_trip(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "hg_platforms/base.py", '"""Base support module."""\n')
    _write(workspace / "hg_platforms/__init__.py", '"""Package marker."""\n')
    _write(workspace / "hg_platforms/fourclaw/create_fourclaw_thread.py", '"""Create a thread."""\n')
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.delenv("HG_GATEWAY_STORE", raising=False)

    items = inventory_tool_registry(workspace)
    assert {item.tool_kind for item in items} == {"support", "script"}
    assert any(item.platform_id == "fourclaw" for item in items)

    with get_connection(str(db_path)) as conn:
        summary = sync_tool_registry(conn, root=workspace)
        assert summary["documents"] == 3
        assert summary["versions"] == 3
        assert summary["created"] == 3

        inventory = list_tool_inventory(conn)
        assert len(inventory) == 3
        entry = get_tool_registry_entry(conn, "hg_platforms.fourclaw.create_fourclaw_thread")
        assert entry is not None
        assert entry["tool_kind"] == "script"
        assert entry["versions"][0]["version_number"] == 1
        stats = get_tool_registry_summary(conn)
        assert stats["total_tools"] == 3
        assert stats["total_versions"] == 3

        _write(workspace / "hg_platforms/fourclaw/create_fourclaw_thread.py", '"""Create a thread updated."""\n')
        summary2 = sync_tool_registry(conn, root=workspace)
        assert summary2["versions"] == 1
        assert summary2["updated"] == 1
        entry2 = get_tool_registry_entry(conn, "hg_platforms.fourclaw.create_fourclaw_thread")
        assert entry2 is not None
        assert entry2["versions"][0]["version_number"] == 2


def test_task_registry_job_registry_refreshes_on_db_change(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.delenv("HG_GATEWAY_STORE", raising=False)

    with get_connection(str(db_path)) as conn:
        from hg_gateway.task_registry import sync_task_registry

        sync_task_registry(conn)
        conn.commit()
        initial = get_job_info("fourclaw-auto-post")
        assert initial is not None
        assert initial.get("sandbox_mode") == "sandbox"

        row = conn.execute(
            "SELECT payload_json FROM task_registry_entries WHERE task_name = ?",
            ("fourclaw-auto-post",),
        ).fetchone()
        payload = json.loads(row["payload_json"])
        payload["sandbox_mode"] = "direct"
        conn.execute(
            "UPDATE task_registry_entries SET payload_json = ?, updated_at = ? WHERE task_name = ?",
            (json.dumps(payload, sort_keys=True), "9999-12-31T23:59:59Z", "fourclaw-auto-post"),
        )
        conn.commit()

    refreshed = get_job_info("fourclaw-auto-post")
    assert refreshed is not None
    assert refreshed.get("sandbox_mode") == "direct"
