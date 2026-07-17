"""Tests for hg_core.memory_maintenance."""

import json
from pathlib import Path

import pytest

from hg_core.memory_maintenance import run_memory_maintenance, _last_activity_utc


class TestLastActivityUtc:
    """Test _last_activity_utc."""

    def test_missing_file_returns_none(self, tmp_path):
        assert _last_activity_utc(tmp_path) is None

    def test_empty_dict_returns_none(self, tmp_path):
        (tmp_path / "memory").mkdir(parents=True)
        (tmp_path / "memory" / "automation-sessions.json").write_text("{}", encoding="utf-8")
        assert _last_activity_utc(tmp_path) is None

    def test_returns_max_last_used(self, tmp_path):
        (tmp_path / "memory").mkdir(parents=True)
        (tmp_path / "memory" / "automation-sessions.json").write_text(
            json.dumps({
                "task-a": {"lastUsed": "2026-02-19T10:00:00Z"},
                "task-b": {"lastUsed": "2026-02-19T12:00:00Z"},
            }),
            encoding="utf-8",
        )
        dt = _last_activity_utc(tmp_path)
        assert dt is not None
        assert dt.year == 2026 and dt.month == 2 and dt.day == 19
        assert dt.hour == 12 and dt.minute == 0


class TestRunMemoryMaintenanceIdleTrigger:
    """Test idle_minutes_before_sleep skip behavior."""

    def test_skipped_when_recent_activity(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_core.memory_maintenance.get_registry", lambda: {})
        (tmp_path / "memory" / "automation").mkdir(parents=True)
        (tmp_path / "memory" / "automation" / "automation-sleep-test").mkdir(parents=True)
        config_path = tmp_path / "memory" / "automation" / "sleep_cycle_config.json"
        config_path.write_text(
            json.dumps({"idle_minutes_before_sleep": 60}),
            encoding="utf-8",
        )
        # lastUsed 2 minutes ago
        from datetime import datetime, timezone, timedelta
        two_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (tmp_path / "memory" / "automation-sessions.json").write_text(
            json.dumps({"some-task": {"lastUsed": two_min_ago}}),
            encoding="utf-8",
        )
        result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["sleep-test"])
        assert result.get("skipped") is True
        assert "last activity within last" in result.get("skipped_reason", "")
        assert result.get("agents_processed") == 0

    def test_not_skipped_when_idle_minutes_unset(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_core.memory_maintenance.get_registry", lambda: {})
        (tmp_path / "memory" / "automation" / "automation-sleep-test").mkdir(parents=True)
        # No sleep_cycle_config or idle_minutes_before_sleep null -> run proceeds
        result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["sleep-test"])
        assert result.get("skipped", False) is False
        assert result.get("agents_processed") == 1

    def test_skipped_when_no_sessions_file_and_idle_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_core.memory_maintenance.get_registry", lambda: {})
        (tmp_path / "memory" / "automation" / "automation-sleep-test").mkdir(parents=True)
        (tmp_path / "memory" / "automation" / "sleep_cycle_config.json").write_text(
            json.dumps({"idle_minutes_before_sleep": 60}),
            encoding="utf-8",
        )
        # No automation-sessions.json
        result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["sleep-test"])
        assert result.get("skipped") is True
        assert "no sessions file" in result.get("skipped_reason", "").lower() or "invalid" in result.get("skipped_reason", "").lower()
        assert result.get("agents_processed") == 0


class TestRunIndexAfterSleep:
    """Test that FTS indexer runs after GC when run_index_after_sleep is true."""

    def test_indexer_invoked_when_run_index_after_sleep_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_core.memory_maintenance.get_registry", lambda: {})
        (tmp_path / "memory" / "automation" / "automation-idx-agent").mkdir(parents=True)
        (tmp_path / "memory" / "automation" / "sleep_cycle_config.json").write_text(
            json.dumps({"run_index_after_sleep": True}),
            encoding="utf-8",
        )
        calls = []
        def fake_index_agent(workspace_root, agent_id):
            calls.append((str(workspace_root), agent_id))
        monkeypatch.setattr("hg_memory.index_agent", fake_index_agent)
        result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["idx-agent"])
        assert result.get("skipped", False) is False
        assert result.get("agents_processed") == 1
        assert len(calls) == 1
        assert calls[0][1] == "idx-agent"

    def test_indexer_not_invoked_when_run_index_after_sleep_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_core.memory_maintenance.get_registry", lambda: {})
        (tmp_path / "memory" / "automation" / "automation-no-idx").mkdir(parents=True)
        (tmp_path / "memory" / "automation" / "sleep_cycle_config.json").write_text(
            json.dumps({"run_index_after_sleep": False}),
            encoding="utf-8",
        )
        calls = []
        def fake_index_agent(workspace_root, agent_id):
            calls.append(agent_id)
        monkeypatch.setattr("hg_memory.index_agent", fake_index_agent)
        result = run_memory_maintenance(workspace_root=tmp_path, agents_filter=["no-idx"])
        assert result.get("agents_processed") == 1
        assert len(calls) == 0
