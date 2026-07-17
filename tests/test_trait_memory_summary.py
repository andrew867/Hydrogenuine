"""Tests for trait judge memory summary (Pack2-02)."""

import json
import pytest
from pathlib import Path

from hg_core.trait_judge.memory_summary import (
    build_memory_summary,
    get_memory_summary_for_entity,
    _rule_based_summary,
    _select_memories,
)


def test_rule_based_summary_structure():
    memories = [
        {"id": "a1", "content": "First fact."},
        {"id": "a2", "content": "Second fact."},
    ]
    out = _rule_based_summary(memories)
    assert "summary_text" in out
    assert "key_facts" in out
    assert "conflicts" in out
    assert "evidence_ids" in out
    assert out["evidence_ids"] == ["a1", "a2"]
    assert isinstance(out["key_facts"], list)
    assert isinstance(out["conflicts"], list)


def test_build_memory_summary_returns_structure():
    out = build_memory_summary("nonexistent-entity", workspace_root=Path.cwd())
    assert "summary_text" in out
    assert "key_facts" in out
    assert "conflicts" in out
    assert "evidence_ids" in out


def test_get_memory_summary_for_entity_includes_updated_at():
    out = get_memory_summary_for_entity("e1", workspace_root=Path.cwd(), cache_get=None, cache_set=None)
    assert "updated_at" in out
    assert "summary_text" in out
    assert "evidence_ids" in out
