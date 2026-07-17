"""
Pack3 Phase 2: Replay bundle tests.

- Build bundle from chat, validate schema and hash chain
- Replay read-only timeline matches transcript
- Diff two bundles produces deterministic diff output
"""

import json
import os
import pytest
from pathlib import Path

from hg_gateway.bundle import (
    build_bundle,
    diff_bundles,
    get_bundles_root,
    replay_read_only,
    validate_bundle,
)
from hg_gateway.store import get_store
from hg_gateway import store as store_module


@pytest.fixture
def store_sqlite(tmp_path):
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    store_module._store = None
    s = get_store()
    try:
        yield s
    finally:
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


@pytest.fixture
def bundle_root(tmp_path):
    os.environ["HG_BUNDLES_ROOT"] = str(tmp_path / "bundles")
    try:
        yield Path(os.environ["HG_BUNDLES_ROOT"])
    finally:
        os.environ.pop("HG_BUNDLES_ROOT", None)


def test_build_and_validate_bundle(store_sqlite, bundle_root):
    """Build bundle from a chat; validate structure and hash chain."""
    tenant_id = "default"
    chat_id = store_sqlite.chat_create(tenant_id, title="Bundle test")
    store_sqlite.message_add(tenant_id, chat_id, "user", "Hello")
    store_sqlite.message_add(tenant_id, chat_id, "assistant", "Hi there", agent_id="primary")
    bundle_id, bundle_dir = build_bundle(tenant_id, chat_id, store_sqlite)
    assert bundle_id
    assert bundle_dir.is_dir()
    assert (bundle_dir / "metadata.json").exists()
    assert (bundle_dir / "transcript.jsonl").exists()
    assert (bundle_dir / "approvals.jsonl").exists()
    assert (bundle_dir / "prompts.jsonl").exists()
    assert (bundle_dir / "hashes.json").exists()
    meta = json.loads((bundle_dir / "metadata.json").read_text(encoding="utf-8"))
    assert meta["tenant_id"] == tenant_id
    assert meta["chat_id"] == chat_id
    assert meta["message_count"] == 2
    ok, errors = validate_bundle(bundle_dir)
    assert ok, errors
    assert not errors


def test_replay_read_only_matches_transcript(store_sqlite, bundle_root):
    """Replay timeline contains messages in order."""
    tenant_id = "default"
    chat_id = store_sqlite.chat_create(tenant_id, title="Replay test")
    store_sqlite.message_add(tenant_id, chat_id, "user", "A")
    store_sqlite.message_add(tenant_id, chat_id, "assistant", "B", agent_id="p")
    _, bundle_dir = build_bundle(tenant_id, chat_id, store_sqlite)
    timeline = replay_read_only(bundle_dir)
    assert len(timeline) >= 2
    messages = [t["data"] for t in timeline if t.get("type") == "message"]
    assert len(messages) == 2
    assert messages[0].get("role") == "user"
    assert messages[1].get("role") == "assistant"
    # Content may be redacted in bundle
    assert "content" in messages[0] and "content" in messages[1]


def test_validate_bundle_fails_on_missing_file(tmp_path):
    """Validate returns errors when a required file is missing."""
    (tmp_path / "metadata.json").write_text("{}")
    ok, errors = validate_bundle(tmp_path)
    assert not ok
    assert any("transcript" in e or "hashes" in e for e in errors)


def test_diff_bundles_same_content_empty_diff(store_sqlite, bundle_root):
    """Two identical bundles -> diff is empty."""
    tenant_id = "default"
    chat_id = store_sqlite.chat_create(tenant_id, title="Same")
    store_sqlite.message_add(tenant_id, chat_id, "user", "X")
    _, dir1 = build_bundle(tenant_id, chat_id, store_sqlite)
    _, dir2 = build_bundle(tenant_id, chat_id, store_sqlite)
    diffs = diff_bundles(dir1, dir2)
    assert len(diffs) == 0


def test_diff_bundles_different_content_has_diff(store_sqlite, bundle_root):
    """Two bundles with different message count -> diff includes count difference."""
    tenant_id = "default"
    c1 = store_sqlite.chat_create(tenant_id, title="One")
    c2 = store_sqlite.chat_create(tenant_id, title="Two")
    store_sqlite.message_add(tenant_id, c1, "user", "A")
    store_sqlite.message_add(tenant_id, c2, "user", "A")
    store_sqlite.message_add(tenant_id, c2, "assistant", "B", agent_id="p")
    _, dir1 = build_bundle(tenant_id, c1, store_sqlite)
    _, dir2 = build_bundle(tenant_id, c2, store_sqlite)
    diffs = diff_bundles(dir1, dir2)
    assert any(d.get("kind") == "message_count" for d in diffs)
