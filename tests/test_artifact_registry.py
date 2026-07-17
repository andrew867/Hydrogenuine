from __future__ import annotations

from pathlib import Path

from hg_gateway.artifact_registry import (
    get_artifact_inventory_summary,
    get_artifact_registry_entry,
    inventory_artifacts,
    list_artifact_inventory,
    list_artifact_versions,
    sync_artifact_registry,
)
from hg_gateway.db import get_connection


def _write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def test_inventory_and_sync_artifact_registry(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write(workspace / "memory/overseer/decision_log.jsonl", "{\"event\":1}\n")
    _write(workspace / "memory/artifacts/social/post1.json", "{\"post\":true}\n")
    _write(workspace / "memory/archive/run-1.json", "{\"archived\":true}\n")
    _write(workspace / "memory/tenants/default/exports/run-1/graph.json", "{\"run\":1}\n")
    _write(workspace / "docs/proofs/out/proof-1/summary.json", "{\"proof\":true}\n")
    _write(workspace / "docs/ux/screenshots/home.png", b"png")
    _write(workspace / "backups/backup-1/gateway.sql", "schema\n")

    items = inventory_artifacts(workspace)
    class_keys = {item.class_key for item in items}
    assert class_keys == {"archive_snapshot", "backup", "screenshot", "artifact", "snapshot", "log"}

    db_path = tmp_path / "gateway.sqlite3"
    with get_connection(str(db_path)) as conn:
        summary = sync_artifact_registry(conn, root=workspace)
        assert summary["artifacts"] == len(items)
        assert summary["versions"] == len(items)

        overview = get_artifact_inventory_summary(conn)
        assert overview["total_artifacts"] == len(items)
        assert {row["class_key"] for row in overview["by_class"]} == class_keys

        entries = list_artifact_inventory(conn)
        assert len(entries) == len(items)

        backup_entry = next(row for row in entries if row["class_key"] == "backup")
        fetched = get_artifact_registry_entry(conn, backup_entry["artifact_id"])
        assert fetched is not None
        assert fetched["file_path"].endswith("gateway.sql")
        assert len(fetched["versions"]) == 1

        _write(workspace / "memory/overseer/decision_log.jsonl", "{\"event\":2}\n")
        changed = sync_artifact_registry(conn, root=workspace)
        assert changed["updated"] == 1
        log_entry = next(row for row in list_artifact_inventory(conn, "log") if row["file_path"].endswith("decision_log.jsonl"))
        versions = list_artifact_versions(conn, log_entry["artifact_id"])
        assert len(versions) == 2
