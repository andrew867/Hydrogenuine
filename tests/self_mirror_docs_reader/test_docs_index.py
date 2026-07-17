"""Docs index tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.docs_reader import build_docs_index


def test_docs_index_ready():
    idx = build_docs_index()
    assert idx.status.value in {"ready", "partial"}
    assert all(not e.excluded or e.exclude_reason for e in idx.entries if hasattr(idx, "entries"))


def test_docs_no_env_paths():
    idx = build_docs_index()
    for e in idx.entries:
        assert ".env" not in e.path.lower()
