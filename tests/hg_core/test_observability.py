"""
Tests for observability: log_decision, post/feedback/decision IDs.
See docs/specs/observability_spec.md.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from hg_core.observability import get_run_id, log_decision
from hg_core.session_manager import save_session_memory
from hg_core.wrappers.decision_context import record_decision
from hg_gateway.shared_storage import list_agent_decisions


def test_get_run_id_returns_12_char_hex():
    """get_run_id returns a 12-character hex string."""
    run_id = get_run_id()
    assert isinstance(run_id, str)
    assert len(run_id) == 12
    assert all(c in "0123456789abcdef" for c in run_id)


def test_log_decision_writes_structured_line(tmp_path):
    """log_decision appends a JSONL line with entity_id, timestamp, event_type, payload."""
    with patch("hg_core.observability.get_workspace_root", return_value=tmp_path):
        log_decision("test-agent", "topic", "current_events", workspace_root=tmp_path)
    log_path = tmp_path / "memory" / "overseer" / "decision_log.jsonl"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["entity_id"] == "test-agent"
    assert entry["event_type"] == "decision"
    assert entry["payload"] == {"key": "topic", "value": "current_events"}
    assert "timestamp" in entry


def test_save_session_memory_adds_id_to_posts(tmp_path):
    """save_session_memory adds id to each post that does not have one."""
    with patch("hg_core.session_manager.get_automation_memory_dir", return_value=tmp_path / "memory" / "automation" / "automation-test-agent"):
        save_session_memory("automation-test-agent", {"posts": [{"content": "hello"}, {"id": "existing-id", "content": "world"}]})
    posts_file = tmp_path / "memory" / "automation" / "automation-test-agent" / "posts.json"
    assert posts_file.exists()
    data = json.loads(posts_file.read_text(encoding="utf-8"))
    posts = data["posts"]
    assert len(posts) == 2
    assert "id" in posts[0]
    assert len(posts[0]["id"]) == 12
    assert posts[1]["id"] == "existing-id"


def test_record_decision_includes_decision_id(tmp_path):
    """record_decision adds decision_id to the decision record."""
    gateway_db = tmp_path / "gateway.sqlite3"
    with (
        patch("hg_core.wrappers.decision_context.get_automation_memory_dir", return_value=tmp_path / "memory" / "automation" / "automation-test-agent"),
        patch("hg_core.wrappers.decision_context.get_workspace_root", return_value=tmp_path),
        patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(gateway_db)}, clear=False),
    ):
        result = record_decision("test-agent", "post", "test rationale")
        assert result["success"] is True
        assert "decision_id" in result["decision"]
        assert len(result["decision"]["decision_id"]) == 12
        shared = list_agent_decisions("test-agent", limit=10)
        assert shared
        assert shared[0]["decision_id"] == result["decision"]["decision_id"]


def test_generate_feedback_items_have_id():
    """generate_feedback produces feedback items with id field."""
    from hg_overseer.overseer_core.overseer_analyzer import generate_feedback
    analysis_results = {
        "test-agent": {
            "post_quality": {"issues": [{"type": "low_quality", "message": "Test issue"}], "recommendations": []},
        },
    }
    thresholds = {}
    items = generate_feedback(analysis_results, thresholds)
    assert len(items) >= 1
    for item in items:
        assert "id" in item
        assert len(item["id"]) == 12


def test_inject_feedback_writes_feedback_id(tmp_path):
    """inject_feedback writes Feedback ID line when item has id."""
    from hg_overseer.overseer_core.overseer_analyzer import inject_feedback
    agent_file = tmp_path / "2026-02-19.md"
    agent_file.write_text("# test-agent - 2026-02-19\n\n", encoding="utf-8")
    feedback = [
        {"id": "abc123def456", "agent": "test-agent", "timestamp": "2026-02-19T12:00:00", "severity": "info", "status": "new", "description": "Test"},
    ]
    inject_feedback(agent_file, feedback)
    content = agent_file.read_text(encoding="utf-8")
    assert "**Feedback ID:** abc123def456" in content


def test_generate_feedback_items_have_required_shape():
    """generate_feedback produces items with required fields: agent, timestamp, severity, status."""
    from hg_overseer.overseer_core.overseer_analyzer import generate_feedback
    analysis_results = {
        "test-agent": {
            "post_quality": {"issues": [{"type": "low_quality", "message": "Test issue"}], "recommendations": []},
        },
    }
    thresholds = {}
    items = generate_feedback(analysis_results, thresholds)
    assert len(items) >= 1
    for item in items:
        assert "agent" in item and isinstance(item["agent"], str)
        assert "timestamp" in item and isinstance(item["timestamp"], str)
        assert "severity" in item and isinstance(item["severity"], str)
        assert "status" in item and isinstance(item["status"], str)


def test_validate_feedback_item_rejects_missing_required():
    """validate_feedback_item returns False for items missing required fields."""
    from hg_overseer.overseer_core.overseer_schemas import validate_feedback_item
    valid = {"agent": "a", "timestamp": "2026-02-19T12:00:00", "severity": "info", "status": "new"}
    ok, err = validate_feedback_item(valid)
    assert ok is True
    assert err is None
    for key in ("agent", "timestamp", "severity", "status"):
        bad = {k: v for k, v in valid.items() if k != key}
        ok, err = validate_feedback_item(bad)
        assert ok is False
        assert err is not None and key in err.lower()


def test_validate_and_warn_feedback_list_invalid_payload():
    """validate_and_warn_feedback_list returns False for list with invalid item."""
    from hg_overseer.overseer_core.overseer_schemas import validate_and_warn_feedback_list
    valid_item = {"agent": "a", "timestamp": "2026-02-19T12:00:00", "severity": "info", "status": "new"}
    assert validate_and_warn_feedback_list([valid_item]) is True
    invalid_item = {"agent": "a"}  # missing timestamp, severity, status
    assert validate_and_warn_feedback_list([invalid_item]) is False
    assert validate_and_warn_feedback_list([valid_item, invalid_item]) is False
