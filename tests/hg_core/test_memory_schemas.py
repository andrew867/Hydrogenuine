"""
Tests for memory file schemas (posts.json, decisions.json).
See docs/specs/memory_and_feedback_schemas_spec.md.
"""

import json
import pytest
from hg_gateway.operational_state_ledger import load_operational_json_state
from hg_gateway.shared_storage import list_agent_decisions
from hg_core.memory_schemas import (
    validate_posts_file,
    validate_decisions_file,
    validate_and_warn_posts_file,
    validate_and_warn_decisions_file,
)


def test_posts_file_valid():
    """Valid posts.json structure passes validation."""
    data = {"posts": [{"id": "1", "content": "hello"}, {"platform": "moltbook"}]}
    ok, err = validate_posts_file(data)
    assert ok is True
    assert err is None


def test_posts_file_missing_posts_key():
    """Root without posts key fails."""
    ok, err = validate_posts_file({})
    assert ok is False
    assert "posts" in (err or "").lower()


def test_posts_file_posts_not_list():
    """posts value not a list fails."""
    ok, err = validate_posts_file({"posts": {}})
    assert ok is False
    assert err is not None


def test_posts_file_item_not_dict():
    """Post item not a dict fails."""
    ok, err = validate_posts_file({"posts": ["not", "dicts"]})
    assert ok is False
    assert "dict" in (err or "").lower()


def test_decisions_file_valid():
    """Valid decisions.json structure passes validation."""
    data = {
        "decisions": [
            {"action": "post", "rationale": "Because", "timestamp": "2026-02-19T12:00:00"},
            {"action": "skip", "rationale": "No content"},
        ]
    }
    ok, err = validate_decisions_file(data)
    assert ok is True
    assert err is None


def test_decisions_file_missing_decisions_key():
    """Root without decisions key fails."""
    ok, err = validate_decisions_file({})
    assert ok is False
    assert "decisions" in (err or "").lower()


def test_decisions_file_missing_action():
    """Decision missing action fails."""
    ok, err = validate_decisions_file({"decisions": [{"rationale": "x"}]})
    assert ok is False
    assert "action" in (err or "").lower()


def test_decisions_file_missing_rationale():
    """Decision missing rationale fails."""
    ok, err = validate_decisions_file({"decisions": [{"action": "post"}]})
    assert ok is False
    assert "rationale" in (err or "").lower()


def test_validate_and_warn_returns_bool():
    """validate_and_warn_* return True for valid, False for invalid."""
    assert validate_and_warn_posts_file({"posts": []}) is True
    assert validate_and_warn_posts_file({}) is False
    assert validate_and_warn_decisions_file({"decisions": [{"action": "a", "rationale": "b"}]}) is True
    assert validate_and_warn_decisions_file({"decisions": []}) is True
    assert validate_and_warn_decisions_file({"decisions": [{"action": "a"}]}) is False


def test_session_manager_write_path_produces_valid_files(tmp_path, monkeypatch):
    """save_session_memory writes the DB-backed session payload plus decision context."""
    from unittest.mock import patch
    from hg_core.session_manager import save_session_memory

    db_path = tmp_path / "memory" / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))

    memory_dir = tmp_path / "memory" / "automation" / "automation-test-agent"
    memory_dir.mkdir(parents=True)
    with patch("hg_core.session_manager.get_automation_memory_dir", return_value=memory_dir):
        save_session_memory("automation-test-agent", {"posts": [{"id": "1", "content": "hi"}]})
        save_session_memory("automation-test-agent", {"decision_context": {"action": "post", "rationale": "test"}})

    state = load_operational_json_state(tmp_path, state_key="automation:session_memory:automation-test-agent")
    assert state["present"] is True
    payload = state["payload"]
    assert isinstance(payload.get("posts"), list)
    assert payload["posts"][0]["content"] == "hi"
    decisions = list_agent_decisions("test-agent", limit=10)
    assert decisions
    assert decisions[0]["action"] == "post"
