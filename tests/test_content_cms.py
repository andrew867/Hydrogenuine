from __future__ import annotations

from pathlib import Path

from hg_gateway.content_cms import (
    get_content_inventory_summary,
    inventory_content,
    list_content_inventory,
    sync_content_inventory,
)
from hg_gateway.db import get_connection


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_inventory_classifies_editable_content(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "skills/automation/tasks/example-task.md", "# Task Title\nTask body.\n")
    _write(workspace / "skills/automation/README.md", "# Skill Title\nSkill body.\n")
    _write(workspace / "docs/runbooks/EXAMPLE.md", "# Runbook Title\nRunbook body.\n")
    _write(workspace / ".cursor/plans/2026-03-22/example/00_README.md", "# Plan Title\nPlan body.\n")
    _write(workspace / ".cursor/plans/archive/old/legacy.md", "# Archived Plan\nSkip me.\n")
    _write(workspace / "SOUL.md", "# Soul Title\nSoul body.\n")
    _write(workspace / "skills/automation/personas/fourclaw/default/HEART.md", "# Heart Title\nHeart body.\n")

    items = inventory_content(workspace)
    classes = {item.class_key for item in items}

    assert classes == {"task", "skill", "runbook", "plan", "persona_meta"}
    assert any(item.title == "Task Title" and item.class_key == "task" for item in items)
    assert any(item.title == "Skill Title" and item.class_key == "skill" for item in items)
    assert any(item.title == "Runbook Title" and item.class_key == "runbook" for item in items)
    assert any(item.title == "Plan Title" and item.class_key == "plan" for item in items)
    assert any(item.title == "Soul Title" and item.class_key == "persona_meta" for item in items)
    assert any(item.title == "Heart Title" and item.class_key == "persona_meta" for item in items)
    assert all("archive" not in item.file_path for item in items)


def test_sync_content_inventory_seeds_classes_and_versions(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "skills/automation/tasks/example-task.md", "# Task Title\nTask body.\n")
    _write(workspace / "docs/runbooks/EXAMPLE.md", "# Runbook Title\nRunbook body.\n")
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.delenv("HG_GATEWAY_STORE", raising=False)

    with get_connection(str(db_path)) as conn:
        summary = sync_content_inventory(conn, root=workspace)
        assert summary["classes"] == 5
        assert summary["documents"] == 2
        assert summary["versions"] == 2
        assert summary["created"] == 2
        rows = conn.execute("SELECT class_key, COUNT(*) AS count FROM content_documents GROUP BY class_key ORDER BY class_key").fetchall()
        assert [dict(row) for row in rows] == [{"class_key": "runbook", "count": 1}, {"class_key": "task", "count": 1}]
        class_rows = conn.execute("SELECT class_key FROM content_document_classes ORDER BY class_key").fetchall()
        assert [row["class_key"] for row in class_rows] == ["persona_meta", "plan", "runbook", "skill", "task"]
        inventory = list_content_inventory(conn)
        assert len(inventory) == 2
        assert {row["class_key"] for row in inventory} == {"task", "runbook"}
        summary2 = get_content_inventory_summary(conn)
        assert summary2["total_documents"] == 2
        assert summary2["total_versions"] == 2
        assert {row["class_key"] for row in summary2["by_class"]} == {"task", "runbook"}

        # Re-run without changes: version count should stay stable.
        summary3 = sync_content_inventory(conn, root=workspace)
        assert summary3["versions"] == 0
        assert summary3["unchanged"] == 2
        assert summary3["updated"] == 0

        # Change one file and ensure a new version is created.
        _write(workspace / "skills/automation/tasks/example-task.md", "# Task Title\nTask body updated.\n")
        summary4 = sync_content_inventory(conn, root=workspace)
        assert summary4["versions"] == 1
        assert summary4["updated"] == 1
        version_rows = conn.execute(
            "SELECT content_id, version_number, state FROM content_document_versions WHERE content_id LIKE 'task:%' ORDER BY version_number"
        ).fetchall()
        assert [dict(row) for row in version_rows] == [
            {"content_id": "task:skills/automation/tasks/example-task.md", "version_number": 1, "state": "imported"},
            {"content_id": "task:skills/automation/tasks/example-task.md", "version_number": 2, "state": "imported"},
        ]
