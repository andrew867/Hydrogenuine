"""Integration tests for run_memory_maintenance (sleep cycle)."""

import json
from pathlib import Path

import pytest

from hg_core.memory_maintenance import run_memory_maintenance


def test_run_memory_maintenance_writes_sleep_receipt_and_log(tmp_path, monkeypatch):
    """Run maintenance on a temp workspace with one agent; assert last_sleep_summary and sleep_log."""
    # Force discovery from disk (not registry) so tmp_path agents are used
    monkeypatch.setattr(
        "hg_core.memory_maintenance.get_registry",
        lambda: {},
    )
    (tmp_path / "memory" / "automation" / "automation-sleep-test").mkdir(parents=True)
    (tmp_path / "memory" / "automation" / "automation-sleep-test" / "2026-02-19.md").write_text(
        "## Today\n\nActivity.", encoding="utf-8"
    )

    result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["sleep-test"])

    assert result.get("errors") == []
    assert "sleep-test" in [a["agent_id"] for a in result.get("per_agent", [])]

    agent_dir = tmp_path / "memory" / "automation" / "automation-sleep-test"
    summary_file = agent_dir / "last_sleep_summary.json"
    assert summary_file.exists()
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert "at" in summary
    assert "promoted" in summary
    assert "nothing_lost" in summary

    sleep_log = tmp_path / "memory" / "overseer" / "sleep_log.jsonl"
    assert sleep_log.exists()
    lines = [ln.strip() for ln in sleep_log.read_text(encoding="utf-8").strip().splitlines() if ln.strip()]
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry.get("agent_id") in ("sleep-test", "automation-sleep-test")
    assert "timestamp" in entry


def test_run_memory_maintenance_archives_old_daily_logs(tmp_path, monkeypatch):
    """With old daily logs, assert archive/ is populated after run."""
    monkeypatch.setattr(
        "hg_core.memory_maintenance.get_registry",
        lambda: {},
    )
    agent_dir = tmp_path / "memory" / "automation" / "automation-archive-test"
    agent_dir.mkdir(parents=True)
    (agent_dir / "2025-12-01.md").write_text("Old.", encoding="utf-8")
    (agent_dir / "2026-02-19.md").write_text("Recent.", encoding="utf-8")

    run_memory_maintenance(workspace_root=tmp_path, agents_filter=["archive-test"])

    archive_dir = agent_dir / "archive"
    assert archive_dir.exists()
    assert (archive_dir / "2025-12-01.md").exists()
    assert not (agent_dir / "2025-12-01.md").exists()
    assert (agent_dir / "2026-02-19.md").exists()


def test_run_memory_maintenance_honors_operational_sleep_request_and_mirrors_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "hg_core.memory_maintenance.get_registry",
        lambda: {},
    )
    operational_dir = tmp_path / "memory" / "automation" / "automation-moltbook"
    legacy_dir = tmp_path / "memory" / "automation" / "automation-moltbook-engage"
    operational_dir.mkdir(parents=True)
    legacy_dir.mkdir(parents=True)
    (operational_dir / "sleep_request.json").write_text(
        json.dumps({"requested_at": "2026-03-08T22:00:00Z", "task": "moltbook-engage"}),
        encoding="utf-8",
    )
    (operational_dir / "2026-03-08.md").write_text("Operational activity.", encoding="utf-8")

    result = run_memory_maintenance(workspace_root=tmp_path)

    assert result.get("skipped") is False
    assert "moltbook" in [a["agent_id"] for a in result.get("per_agent", [])]
    assert (operational_dir / "last_sleep_summary.json").exists()
    assert (legacy_dir / "last_sleep_summary.json").exists()
    assert not (operational_dir / "sleep_request.json").exists()
