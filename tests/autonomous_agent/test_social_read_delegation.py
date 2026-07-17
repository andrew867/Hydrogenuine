"""Social read delegation tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.social_capability.read import read_social  # noqa: E402
from hg_runtime.social_capability.schema import SocialReadRequest, SocialSurface, new_id  # noqa: E402


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)
    monkeypatch.delenv("HG_MOLTBOOK_TOKEN", raising=False)
    monkeypatch.delenv("HG_SOCIAL_LIVE_READ", raising=False)
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)
    monkeypatch.setattr(
        "hg_runtime.social_capability.credentials.load_operator_social_env",
        lambda **kw: [],
    )


def test_fixture_read_denied_by_default(monkeypatch):
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)
    req = SocialReadRequest(new_id("read"), SocialSurface.FIXTURE, live=False)
    result = read_social(req)
    assert result.items == []
    assert "RED_FIXTURE" in result.trust_disposition or result.trust_disposition == "RED_FIXTURE_USED_IN_RUNTIME"
    assert result.trust_ok is False


def test_explicit_fixture_read_labelled(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    req = SocialReadRequest(new_id("read"), SocialSurface.FIXTURE, live=False)
    result = read_social(req)
    assert result.trust_disposition == "YELLOW_FIXTURE_REHEARSAL"
    assert len(result.items) > 0


def test_read_delegates_live_requests_to_live_bridge(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "tok")

    calls: list[str] = []

    def mock_surface(surface, **kwargs):
        calls.append(str(surface))
        from hg_runtime.social_capability.live_bridge import LiveReadResult, LiveReadVerdict
        from hg_runtime.social_capability.read_receipts import (
            LiveReadCredentialStatus,
            build_live_read_receipt,
        )

        receipt = build_live_read_receipt(
            request_id=kwargs.get("request_id", "x"),
            surface="moltbook",
            runtime_mode="local_dev",
            fixture_mode=False,
            credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
            api_called=True,
            api_call_kind="GET",
            item_count=0,
            source_refs=[],
            read_started_at="2026-06-17T00:00:00+00:00",
            read_finished_at="2026-06-17T00:00:00+00:00",
            latency_ms=1,
            verdict=LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED,
        )
        from hg_runtime.social_capability.live_bridge import LiveReadResult as LR

        return LR(
            request_id=kwargs.get("request_id", "x"),
            surface="moltbook",
            items=[],
            receipt=receipt,
            verdict=LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED,
            credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
        )

    monkeypatch.setattr(
        "hg_runtime.social_capability.read.read_surface_live",
        mock_surface,
    )
    req = SocialReadRequest(new_id("read"), SocialSurface.MOLTBOOK, live=True)
    result = read_social(req)
    assert calls
    assert result.trust_disposition == "YELLOW_NO_ITEMS_RETURNED"


def test_live_read_disabled_returns_honest_yellow_not_fixture(monkeypatch):
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)
    monkeypatch.delenv("HG_SOCIAL_LIVE_READ", raising=False)
    req = SocialReadRequest(new_id("read"), SocialSurface.MOLTBOOK, live=False)
    result = read_social(req)
    assert result.items == []
    assert result.trust_disposition == "YELLOW_LIVE_READ_DISABLED"
    assert result.trust_ok is False
