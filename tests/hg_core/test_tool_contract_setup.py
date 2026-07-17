"""Tests for tool_contract_setup: build_default_tool_contract and job_registry failure visibility."""

import logging
from unittest.mock import patch

import pytest

from hg_core.task_graph.tool_contract_setup import build_default_tool_contract


def test_build_default_tool_contract_job_registry_failure_logs_and_social_tools_remain(caplog):
    """When get_registry() raises, registry still contains built-in social/file/office/moltbook/lifecycle tools and logs a warning."""
    with patch("hg_core.job_registry.get_registry", side_effect=RuntimeError("no workspace")):
        with caplog.at_level(logging.WARNING):
            registry, adapter = build_default_tool_contract()
    assert len(registry.list()) >= 30
    assert registry.get("social.fourclaw.getposts") is not None
    assert registry.get("file.parse") is not None
    assert registry.get("search.fetch_url") is not None
    assert registry.get("lifecycle.wakeup") is not None
    assert registry.get("lifecycle.get_runtime_contract") is not None
    assert registry.get("lifecycle.choose_social_work") is not None
    assert registry.get("lifecycle.dispatch_social_work") is not None
    assert registry.get("lifecycle.request_sleep") is not None
    assert registry.get("knowledge.search") is not None
    assert registry.get("knowledge.read") is not None
    assert registry.get("knowledge.source_status") is not None
    assert "job_registry" in caplog.text or "tool registry empty" in caplog.text.lower()
    assert "no workspace" in caplog.text or "RuntimeError" in caplog.text


def test_build_default_tool_contract_success_registry_non_empty():
    """When get_registry() returns jobs, at least one descriptor is registered."""
    registry, adapter = build_default_tool_contract()
    # Default job_registry has many entries; we only need at least one
    assert len(registry.list()) >= 1
    assert adapter is not None


def test_build_default_tool_contract_registers_lifecycle_tools():
    registry, _adapter = build_default_tool_contract()
    assert registry.get("lifecycle.wakeup").effect_class == "read"
    assert registry.get("lifecycle.get_runtime_contract").effect_class == "read"
    assert registry.get("lifecycle.choose_social_work").effect_class == "read"
    assert registry.get("lifecycle.dispatch_social_work").effect_class == "write"
    assert registry.get("lifecycle.prepare_notification").effect_class == "write"
    assert registry.get("lifecycle.notify_human").effect_class == "write"
    assert registry.get("knowledge.search").effect_class == "read"
    assert registry.get("knowledge.read").effect_class == "read"
    assert registry.get("knowledge.delivery_summary").effect_class == "read"
    assert registry.get("knowledge.source_status").effect_class == "read"
    assert registry.get("social.moltbook.get_post").effect_class == "read"
    assert registry.get("social.moltbook.get_comments").effect_class == "read"
    assert registry.get("social.moltbook.create_post").effect_class == "write"
    assert registry.get("social.moltbook.vote_post").effect_class == "write"
