"""Self mirror snapshot tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.self_model import build_self_snapshot, snapshot_content_hash


def test_self_snapshot_validates():
    snap = build_self_snapshot()
    p = snap.to_payload()
    assert p["advisory_only"] is True
    assert p["permission_granted"] is False
    assert p["authority_created"] is False
    assert p["agent_code_id"] == "agent0"


def test_self_snapshot_hash_stable():
    s1 = build_self_snapshot()
    s2 = build_self_snapshot()
    s1.repo_head = s2.repo_head = "abc123"
    s1.branch = s2.branch = "master"
    assert snapshot_content_hash(s1) == snapshot_content_hash(s2)
