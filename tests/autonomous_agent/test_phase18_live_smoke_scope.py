"""Phase 18 live smoke scope tests."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from hg_runtime.external_write_authority.live_smoke import (
    create_live_smoke_scope,
    file_sha256,
    load_live_smoke_scope,
)


def test_live_scope_requires_operator_ref(tmp_path, monkeypatch):
    monkeypatch.delenv("HG_PHASE18_ALLOW_LIVE_SMOKE", raising=False)
    f = tmp_path / "post.md"
    f.write_text("# test\nhello", encoding="utf-8")
    assert create_live_smoke_scope(
        operator_ref="",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    ) is None


def test_live_scope_max_live_actions_one(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "post.md"
    f.write_text("# test\nhello", encoding="utf-8")
    sha = file_sha256(f)
    monkeypatch.setenv("HG_PHASE18_EXPECTED_CONTENT_SHA256", sha)
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    assert scope is not None
    assert scope.max_live_actions == 1


def test_live_scope_rejects_missing_content_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    monkeypatch.setenv("HG_PHASE18_EXPECTED_CONTENT_SHA256", "deadbeef")
    f = tmp_path / "post.md"
    f.write_text("content", encoding="utf-8")
    assert create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    ) is None


def test_live_scope_rejects_expired_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "post.md"
    f.write_text("x", encoding="utf-8")
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    assert scope is not None
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert scope.is_expired(at=future)
