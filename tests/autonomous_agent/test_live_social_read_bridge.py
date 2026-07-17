"""Live social read bridge tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.social_capability.live_bridge import (  # noqa: E402
    LiveReadRequest,
    LiveReadSurface,
    LiveReadVerdict,
    read_fourclaw_live,
    read_moltbook_live,
)
from hg_runtime.social_capability.read_receipts import validate_live_read_receipt  # noqa: E402


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)
    monkeypatch.delenv("HG_MOLTBOOK_TOKEN", raising=False)
    monkeypatch.delenv("HG_FOURCLAW_TOKEN", raising=False)
    monkeypatch.delenv("MOLTBOOK_API_KEY", raising=False)
    monkeypatch.delenv("FOURCLAW_API_KEY", raising=False)
    monkeypatch.delenv("HG_SOCIAL_MOLTBOOK_TOKEN", raising=False)
    monkeypatch.delenv("HG_SOCIAL_FOURCLAW_TOKEN", raising=False)
    monkeypatch.setattr(
        "hg_runtime.social_capability.credentials.load_operator_social_env",
        lambda **kw: [],
    )


def test_missing_moltbook_credentials_returns_yellow(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    req = LiveReadRequest(request_id="req-mb-miss", surface=LiveReadSurface.MOLTBOOK)
    result = read_moltbook_live(req)
    assert result.verdict == LiveReadVerdict.YELLOW_CREDENTIALS_MISSING
    assert result.items == []
    assert result.receipt.api_called is False


def test_missing_fourclaw_credentials_returns_yellow(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    req = LiveReadRequest(request_id="req-fc-miss", surface=LiveReadSurface.FOURCLAW)
    result = read_fourclaw_live(req)
    assert result.verdict == LiveReadVerdict.YELLOW_CREDENTIALS_MISSING
    assert result.items == []


def test_empty_live_api_response_returns_yellow_not_green(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "test-token-redacted")

    def empty_fetch(**_kwargs):
        return {"ok": True, "posts": [], "count": 0, "http_status": 200}

    req = LiveReadRequest(request_id="req-empty", surface=LiveReadSurface.MOLTBOOK)
    result = read_moltbook_live(req, fetcher=empty_fetch)
    assert result.verdict == LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED
    assert result.verdict != LiveReadVerdict.GREEN_LIVE_READ_OK
    assert result.receipt.item_count == 0


def test_mocked_moltbook_read_writes_receipt_with_source_refs(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "test-token")

    def mock_fetch(**_kwargs):
        return {
            "ok": True,
            "posts": [{"id": "post-abc", "content": "Hello from moltbook", "author": "agent0"}],
            "http_status": 200,
        }

    req = LiveReadRequest(request_id="req-mb-ok", surface=LiveReadSurface.MOLTBOOK)
    result = read_moltbook_live(req, fetcher=mock_fetch)
    assert result.verdict == LiveReadVerdict.GREEN_LIVE_READ_OK
    assert len(result.items) == 1
    assert result.receipt.source_refs == ("moltbook:post:post-abc",)
    assert validate_live_read_receipt(result.receipt) == LiveReadVerdict.GREEN_LIVE_READ_OK


def test_mocked_fourclaw_read_writes_receipt_with_source_refs(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_FOURCLAW_TOKEN", "test-token")

    def mock_fetch(**_kwargs):
        return {
            "ok": True,
            "threads": [{"id": "thread-99", "title": "Thread", "content": "Fourclaw body"}],
            "board": "singularity",
            "http_status": 200,
        }

    req = LiveReadRequest(request_id="req-fc-ok", surface=LiveReadSurface.FOURCLAW)
    result = read_fourclaw_live(req, fetcher=mock_fetch)
    assert result.verdict == LiveReadVerdict.GREEN_LIVE_READ_OK
    assert result.receipt.source_refs == ("fourclaw:thread:thread-99",)
