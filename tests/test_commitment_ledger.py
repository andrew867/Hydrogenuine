from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hg_gateway.commitment_ledger import expire_commitment, fulfill_commitment, list_commitments, record_commitment, summarize_commitments
from hg_gateway.db import get_connection


def test_commitment_ledger_persists_and_summarizes(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    due_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    commitment = record_commitment(
        tmp_path,
        task_name="social-media-underling",
        title="Reply to the latest thread",
        details={"topic": "follow-up"},
        due_at=due_at,
        commitment_kind="promise",
        tenant_id="default",
        entity_id="social-media-underling",
        operational_agent_id="underling-chan",
        created_by="operator_console",
    )

    assert commitment["title"] == "Reply to the latest thread"
    rows = list_commitments(tmp_path, task_name="social-media-underling", limit=10)
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    summary = summarize_commitments(rows)
    assert summary["status"] == "overdue"
    assert summary["overdue_count"] == 1

    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute("SELECT COUNT(*) FROM commitment_records").fetchone()
        assert row[0] == 1
        notification_row = conn.execute("SELECT COUNT(*) FROM human_notifications WHERE kind = 'commitment_recorded'").fetchone()
        assert notification_row[0] == 1


def test_commitment_ledger_fulfill_and_expire_transition(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    commitment = record_commitment(
        tmp_path,
        task_name="social-media-bayman",
        title="Check in with Bayman",
        details={"topic": "status"},
        tenant_id="default",
        entity_id="social-media-bayman",
        operational_agent_id="newfoundland-bayman",
        created_by="operator_console",
    )
    fulfilled = fulfill_commitment(tmp_path, commitment_id=commitment["commitment_id"], resolution_note="completed in rehearsal")
    assert fulfilled is not None
    assert fulfilled["status"] == "fulfilled"
    listed = list_commitments(tmp_path, task_name="social-media-bayman", limit=10)
    assert listed[0]["status"] == "fulfilled"

    expired = record_commitment(
        tmp_path,
        task_name="social-media-bayman",
        title="Legacy follow-up",
        details={},
        tenant_id="default",
        entity_id="social-media-bayman",
        operational_agent_id="newfoundland-bayman",
        created_by="operator_console",
    )
    expired_row = expire_commitment(tmp_path, commitment_id=expired["commitment_id"], resolution_note="no longer needed")
    assert expired_row is not None
    assert expired_row["status"] == "expired"
    listed = list_commitments(tmp_path, task_name="social-media-bayman", limit=10)
    assert {row["status"] for row in listed} >= {"fulfilled", "expired"}
