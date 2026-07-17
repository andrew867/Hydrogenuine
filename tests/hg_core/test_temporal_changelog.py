from hg_core.temporal_changelog import (
    format_temporal_events,
    load_recent_temporal_events,
    record_major_disruption_once,
    record_temporal_event,
)
from hg_gateway.db import get_connection


def test_record_and_load_temporal_event(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    event = record_temporal_event(
        title="Test outage",
        summary="There was a gap because the system was offline.",
        workspace_root=tmp_path,
        kind="outage",
        severity="high",
        affected_entities=["all"],
    )
    rows = load_recent_temporal_events(workspace_root=tmp_path, agent_id="agentchan", limit=5, days=30)
    assert rows
    assert rows[0]["event_id"] == event["event_id"]

    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type = ?", ("temporal_changelog",)).fetchone()
        assert row[0] == 1


def test_format_temporal_events_compacts_for_wake_context():
    rows = [
        {
            "start_at": "2026-03-08T00:00:00Z",
            "title": "Postgres migration",
            "summary": "There was an outage during the cutover.",
        }
    ]
    lines = format_temporal_events(rows, max_items=2)
    assert lines == ["2026-03-08: Postgres migration - There was an outage during the cutover."]


def test_load_recent_temporal_events_filters_minor_internal_noise(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    record_temporal_event(
        title="Minor maintenance",
        summary="Background cleanup completed.",
        workspace_root=tmp_path,
        kind="maintenance",
        severity="info",
        affected_entities=["all"],
    )
    record_temporal_event(
        title="Major outage",
        summary="There was downtime.",
        workspace_root=tmp_path,
        kind="outage",
        severity="high",
        affected_entities=["all"],
    )
    rows = load_recent_temporal_events(workspace_root=tmp_path, agent_id="agentchan", limit=10, days=30)
    titles = [row["title"] for row in rows]
    assert "Major outage" in titles
    assert "Minor maintenance" not in titles


def test_record_major_disruption_once_dedupes_recent_events(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    first = record_major_disruption_once(
        title="Scheduler disruption",
        summary="Scheduled work was delayed.",
        workspace_root=tmp_path,
        dedupe_key="cron_health:major_disruption",
        kind="outage",
        severity="high",
        affected_entities=["all"],
    )
    second = record_major_disruption_once(
        title="Scheduler disruption",
        summary="Scheduled work was delayed.",
        workspace_root=tmp_path,
        dedupe_key="cron_health:major_disruption",
        kind="outage",
        severity="high",
        affected_entities=["all"],
    )
    assert first is not None
    assert second is None
