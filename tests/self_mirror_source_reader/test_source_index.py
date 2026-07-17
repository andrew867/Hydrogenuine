"""Source index exclusion tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.repo_index import index_paths
from hg_runtime.agent_zero_self_mirror.source_reader import build_source_index


def test_source_index_excludes_secrets():
    status, entries = index_paths(["configs"])
    excluded = [e for e in entries if e.excluded]
    assert any(".env" in (e.exclude_reason or "") for e in excluded) or any("forbidden" in (e.exclude_reason or "") for e in excluded)


def test_hg_local_excluded():
    status, entries = index_paths([".hg-local"])
    assert all(e.excluded for e in entries) or len(entries) == 0


def test_source_index_has_entries():
    idx = build_source_index()
    assert idx.status.value in {"ready", "partial"}
    assert len(idx.entries) > 0
