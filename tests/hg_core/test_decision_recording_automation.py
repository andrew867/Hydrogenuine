"""
Tests for automatic decision recording: fourclaw-engage (reply script) and knowledge-research-auto.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from hg_gateway.shared_storage import list_agent_decisions


def test_fourclaw_engage_records_decision_on_reply(tmp_path):
    """_record_fourclaw_engage_decision writes to the shared decision ledger."""
    memory_dir = tmp_path / "memory" / "automation" / "automation-fourclaw-engage"
    memory_dir.mkdir(parents=True)
    with (
        patch("hg_core.wrappers.decision_context.get_automation_memory_dir", return_value=memory_dir),
        patch("hg_core.wrappers.decision_context.get_workspace_root", return_value=tmp_path),
        patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(tmp_path / "gateway.sqlite3")}, clear=False),
    ):
        from hg_platforms.fourclaw.reply_to_fourclaw_thread import _record_fourclaw_engage_decision
        _record_fourclaw_engage_decision("thread-123", {"id": "reply-456"})
        data = list_agent_decisions("fourclaw-engage", limit=10)
    assert data
    last = data[0]
    assert last.get("action", "").find("thread-123") >= 0
    assert "fourclaw" in last.get("rationale", "").lower() or "thread" in last.get("rationale", "").lower()


def test_knowledge_research_record_research_decision_writes_to_memory(tmp_path):
    """record_research_decision writes to the shared decision ledger."""
    memory_dir = tmp_path / "memory" / "automation" / "automation-knowledge-research-auto"
    memory_dir.mkdir(parents=True)
    with (
        patch("hg_core.wrappers.decision_context.get_automation_memory_dir", return_value=memory_dir),
        patch("hg_core.wrappers.decision_context.get_workspace_root", return_value=tmp_path),
        patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(tmp_path / "gateway.sqlite3")}, clear=False),
    ):
        from hg_knowledge.research_agent import record_research_decision
        record_research_decision(
            topic="AI sovereignty",
            file_path="knowledge/tech/ai-sovereignty.md",
            reason="gap",
        )
        data = list_agent_decisions("knowledge-research-auto", limit=10)
    assert data
    last = data[0]
    assert "AI sovereignty" in last.get("action", "")
    assert "knowledge" in last.get("action", "") or "ai-sovereignty" in last.get("action", "")
