from __future__ import annotations

import json

from hg_core.human_notifications import list_human_notifications, record_human_notification
from hg_gateway.db import get_connection


def test_human_notification_ledger_prefers_gateway_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    result = record_human_notification(
        tmp_path,
        task_name="social-media-underling",
        message="Hello from the DB ledger",
        kind="status",
        recipient="The Reverend",
        transport="db_first",
        social_account_id="account-1",
        tenant_id="default",
        operational_agent_id="underling",
    )
    assert result["entry"]["message"] == "Hello from the DB ledger"

    notification_dir = tmp_path / "memory" / "automation" / "notifications"
    notification_dir.mkdir(parents=True, exist_ok=True)
    (notification_dir / "human_notifications.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2000-01-01T00:00:00Z",
                "task_name": "legacy-fallback",
                "kind": "legacy",
                "message": "This file should lose",
                "transport": "file_only",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    items = list_human_notifications(tmp_path, limit=5)
    assert items
    assert items[0]["message"] == "Hello from the DB ledger"
    assert items[0]["task_name"] == "social-media-underling"

    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute("SELECT COUNT(*) FROM human_notifications").fetchone()
        assert row[0] == 1


def test_human_notification_ledger_ignores_jsonl_when_db_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    notification_dir = tmp_path / "memory" / "automation" / "notifications"
    notification_dir.mkdir(parents=True, exist_ok=True)
    (notification_dir / "human_notifications.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-03-21T00:00:00Z",
                "task_name": "file-fallback",
                "kind": "fallback",
                "message": "This came from JSONL",
                "transport": "file_only",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    items = list_human_notifications(tmp_path, limit=5)
    assert items == []
