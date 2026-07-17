"""Tests for hg_lib.duplicate_detector."""

import os
from pathlib import Path

import pytest

from hg_lib.duplicate_detector import content_hash, is_duplicate, get_duplicate_cache_dir


def test_content_hash_deterministic():
    """Same input produces same hash."""
    h1 = content_hash("Hello world", platform="moltbook", mode="auto-post")
    h2 = content_hash("Hello world", platform="moltbook", mode="auto-post")
    assert h1 == h2


def test_content_hash_format():
    """Hash includes version, platform, mode, content_type."""
    h = content_hash("test", platform="x", mode="y", content_type="reply")
    assert h.startswith("v1:x:y:reply:")
    assert len(h.split(":")[-1]) == 64  # sha256 hex


def test_content_hash_normalization():
    """Whitespace normalized for hashing."""
    h1 = content_hash("  hello   world  ")
    h2 = content_hash("hello world")
    assert h1 == h2


def test_is_duplicate_first_call_false(monkeypatch, tmp_path):
    """First call returns False (not duplicate)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    # Re-import to pick up new env
    import importlib
    import hg_lib.duplicate_detector as dd
    importlib.reload(dd)
    assert dd.is_duplicate("unique content 123") is False


def test_is_duplicate_second_call_true(monkeypatch, tmp_path):
    """Second call with same content returns True (duplicate)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    import importlib
    import hg_lib.duplicate_detector as dd
    importlib.reload(dd)
    text = "duplicate test content 456"
    assert dd.is_duplicate(text) is False
    assert dd.is_duplicate(text) is True


def test_get_duplicate_cache_dir_under_workspace_memory(monkeypatch, tmp_path):
    """Cache dir is under workspace memory/duplicate_cache."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    cache_dir = get_duplicate_cache_dir()
    expected = tmp_path / "memory" / "duplicate_cache"
    assert cache_dir == expected
