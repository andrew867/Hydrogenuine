"""Tests for hg_core.semantic_duplicate_detector."""

import importlib
from pathlib import Path

import pytest

from hg_core.semantic_duplicate_detector import (
    check_duplicate_content,
    check_semantic_duplicate_with_content_hash,
    normalize_content,
    SemanticDuplicateDetector,
)


def test_normalize_content():
    """Normalize collapses whitespace and lowercases."""
    assert normalize_content("  Hello   World  ") == "hello world"
    assert normalize_content("") == ""


def test_check_duplicate_content_empty_content():
    """Empty content returns (False, None)."""
    is_dup, dup_of = check_duplicate_content("", [{"content": "x", "id": "1"}])
    assert is_dup is False
    assert dup_of is None


def test_check_duplicate_content_exact_match_via_items(monkeypatch, tmp_path):
    """Exact match in existing_items is detected (after content-hash check)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    import hg_core.semantic_duplicate_detector as sdd
    importlib.reload(sdd)
    items = [{"content": "same text here", "id": "abc"}]
    is_dup, dup_of = sdd.check_duplicate_content("same text here", items)
    assert is_dup is True
    assert dup_of == "abc"


def test_check_duplicate_content_content_hash_first(monkeypatch, tmp_path):
    """Content-hash duplicate returns True before checking items."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    import hg_core.semantic_duplicate_detector as sdd
    importlib.reload(sdd)
    text = "unique content hash test 789"
    # First call: not duplicate, adds to cache
    is_dup1, _ = sdd.check_duplicate_content(text, [])
    assert is_dup1 is False
    # Second call: content-hash hit (empty items, but cache has it)
    is_dup2, dup_of2 = sdd.check_duplicate_content(text, [])
    assert is_dup2 is True
    assert dup_of2 is None


def test_check_semantic_duplicate_with_content_hash_empty():
    """Empty content returns (False, None, 0.0)."""
    is_dup, dup_of, sim = check_semantic_duplicate_with_content_hash("")
    assert is_dup is False
    assert dup_of is None
    assert sim == 0.0


def test_check_semantic_duplicate_with_content_hash_persists(monkeypatch, tmp_path):
    """Content-hash hit on second call returns (True, None, 1.0)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    import hg_core.semantic_duplicate_detector as sdd
    importlib.reload(sdd)
    text = "semantic content hash persist 321"
    is_dup1, _, sim1 = sdd.check_semantic_duplicate_with_content_hash(
        text, platform="test", mode="unit"
    )
    assert is_dup1 is False
    is_dup2, _, sim2 = sdd.check_semantic_duplicate_with_content_hash(
        text, platform="test", mode="unit"
    )
    assert is_dup2 is True
    assert sim2 == 1.0


def test_semantic_detector_history_path():
    """SemanticDuplicateDetector uses memory/automation/content_history.json under workspace."""
    from hg_lib.config import get_memory_dir

    detector = SemanticDuplicateDetector()
    expected_parent = get_memory_dir() / "automation"
    assert detector.history_path.parent == expected_parent
    assert detector.history_path.name == "content_history.json"


def test_semantic_detector_record_and_check(monkeypatch, tmp_path):
    """Record content then check_semantic_duplicate finds it (Jaccard similarity)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    history_file = tmp_path / "memory" / "automation" / "content_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    import hg_core.semantic_duplicate_detector as sdd
    importlib.reload(sdd)

    detector = sdd.SemanticDuplicateDetector(history_path=history_file)
    detector.record_content("hello world test", platform="test", content_id="id1")

    is_dup, dup_of, sim = detector.check_semantic_duplicate("hello world test")
    assert is_dup is True
    assert dup_of == "id1"
    assert sim >= 0.99  # exact match
