"""Tests for hg_memory public API (callers import only from hg_memory)."""

from pathlib import Path

import pytest

from hg_memory import (
    search_memory,
    get_recent_entities,
    index_agent,
    run_indexing_job,
)


def test_hg_memory_exposes_documented_functions():
    """hg_memory exposes search_memory, get_recent_entities, index_agent, run_indexing_job."""
    assert callable(search_memory)
    assert callable(get_recent_entities)
    assert callable(index_agent)
    assert callable(run_indexing_job)


def test_search_memory_returns_list(tmp_path):
    """search_memory(workspace_root, agent_id) returns a list (empty if no DB)."""
    result = search_memory(tmp_path, "test-agent", max_snippets=5, days=7)
    assert isinstance(result, list)


def test_get_recent_entities_returns_list(tmp_path):
    """get_recent_entities(workspace_root, agent_id) returns a list (empty if no DB)."""
    result = get_recent_entities(tmp_path, "test-agent", limit=5)
    assert isinstance(result, list)


def test_index_agent_no_raise(tmp_path):
    """index_agent(workspace_root, agent_id) does not raise (no-op or runs)."""
    index_agent(tmp_path, "test-agent")


def test_run_indexing_job_returns_dict():
    """run_indexing_job() returns dict with agents_processed, total_indexed, total_errors, per_agent."""
    result = run_indexing_job()
    assert isinstance(result, dict)
    assert "agents_processed" in result
    assert "total_indexed" in result
    assert "total_errors" in result
    assert "per_agent" in result
