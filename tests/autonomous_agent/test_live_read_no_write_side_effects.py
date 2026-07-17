"""Live read must not invoke write side effects."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.social_capability.live_bridge import (  # noqa: E402
    LiveReadRequest,
    LiveReadSurface,
    read_moltbook_live,
)


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "tok")
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")


def test_no_publish_called_during_live_read():
    def mock_fetch(**_kwargs):
        return {"ok": True, "posts": [{"id": "p1", "content": "x"}], "http_status": 200}

    with patch("hg_runtime.social_capability.publisher.publish_with_permit") as pub:
        with patch("hg_runtime.social_capability.draft.create_curated_draft") as draft:
            req = LiveReadRequest(request_id="req-nowrite", surface=LiveReadSurface.MOLTBOOK)
            read_moltbook_live(req, fetcher=mock_fetch)
            pub.assert_not_called()
            draft.assert_not_called()


def test_runtime_local_dev_without_enablement_does_not_fake_success(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.social_capability.credentials.load_operator_social_env",
        lambda **kwargs: [],
    )
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)
    monkeypatch.delenv("HG_SOCIAL_LIVE_READ", raising=False)
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    req = LiveReadRequest(request_id="req-disabled", surface=LiveReadSurface.MOLTBOOK)
    result = read_moltbook_live(req)
    assert result.items == []
    assert result.receipt.api_called is False
    assert "DISABLED" in result.verdict.value or "disabled" in (result.receipt.error or "").lower()
