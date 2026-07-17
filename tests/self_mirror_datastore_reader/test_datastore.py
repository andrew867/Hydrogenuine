"""Datastore metadata-only tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.datastore_reader import build_datastore_index


def test_datastore_metadata_only():
    idx = build_datastore_index()
    assert idx.status.value == "ready"
    for s in idx.stores:
        assert s["permission_granted"] is False
        assert "content_policy" in s or "config_path" in s
