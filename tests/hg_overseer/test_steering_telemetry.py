"""Tests for steering telemetry (steering_telemetry_contract): event emission to steering_events.jsonl."""

import json
import pytest
from pathlib import Path

from hg_overseer.overseer_core.overseer_main import _default_steering_telemetry_sink


def test_default_steering_telemetry_sink_writes_event(tmp_path):
    """_default_steering_telemetry_sink appends one JSON line per call to memory/overseer/steering_events.jsonl."""
    sink = _default_steering_telemetry_sink(tmp_path)
    sink("steering_feedback_injected", {
        "agent_id": "test-agent",
        "details": {"count": 2},
    })
    events_path = tmp_path / "memory" / "overseer" / "steering_events.jsonl"
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "steering_feedback_injected"
    assert "timestamp" in entry
    assert entry.get("agent_id") == "test-agent"
    assert entry.get("details", {}).get("count") == 2


def test_default_steering_telemetry_sink_appends_authority_action(tmp_path):
    """Sink appends authority_action_applied event with expected shape."""
    sink = _default_steering_telemetry_sink(tmp_path)
    sink("authority_action_applied", {
        "agent_id": "fourclaw-auto-post",
        "file": "/path/to/task.md",
        "issue_type": "bash_syntax_in_powershell",
        "details": {"changes_made": ["Added warning"]},
    })
    events_path = tmp_path / "memory" / "overseer" / "steering_events.jsonl"
    assert events_path.exists()
    entry = json.loads(events_path.read_text(encoding="utf-8").strip())
    assert entry["event"] == "authority_action_applied"
    assert entry.get("issue_type") == "bash_syntax_in_powershell"
    assert "timestamp" in entry


def test_steering_cycle_completed_event_shape(tmp_path):
    """steering_cycle_completed event has run_id, cycle_id, details with counts."""
    sink = _default_steering_telemetry_sink(tmp_path)
    sink("steering_cycle_completed", {
        "run_id": None,
        "cycle_id": "2026-02-23T12:00:00",
        "details": {"feedback_count": 1, "authority_actions_count": 0, "task_file_edits_count": 0},
    })
    events_path = tmp_path / "memory" / "overseer" / "steering_events.jsonl"
    entry = json.loads(events_path.read_text(encoding="utf-8").strip())
    assert entry["event"] == "steering_cycle_completed"
    assert "details" in entry
    assert "feedback_count" in entry["details"] or "task_file_edits_count" in entry["details"]
