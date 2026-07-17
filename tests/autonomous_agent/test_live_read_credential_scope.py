"""Live read credential scope tests."""
from __future__ import annotations

import pytest

from hg_runtime.live_read_endurance.credential_scope import check_credential_scope, credential_summary
from hg_runtime.live_read_endurance.errors import LiveReadWriteScopeDetected
from hg_runtime.live_read_endurance.schema import LiveReadEnduranceVerdict
from hg_runtime.social_capability.live_bridge import LiveReadSurface


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.live_read_endurance.credential_scope.load_operator_social_env",
        lambda **kwargs: [],
    )
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_SOCIAL_LIVE_REPLY", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    monkeypatch.setenv("HG_EXTERNAL_SEND_ENABLED", "false")
    monkeypatch.setenv("HG_EXTERNAL_SEND_ENABLED", "false")
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)
    monkeypatch.delenv("HG_SOCIAL_LIVE_READ", raising=False)
    monkeypatch.delenv("HG_MOLTBOOK_TOKEN", raising=False)
    monkeypatch.delenv("HG_SOCIAL_MOLTBOOK_TOKEN", raising=False)
    monkeypatch.delenv("MOLTBOOK_API_KEY", raising=False)


def test_credentials_missing_yellow():
    scope = check_credential_scope(LiveReadSurface.MOLTBOOK)
    assert scope.read_allowed is False
    assert scope.write_allowed is False
    assert scope.verdict == LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING


def test_write_scope_red(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "true")
    with pytest.raises(LiveReadWriteScopeDetected):
        check_credential_scope(LiveReadSurface.MOLTBOOK)


def test_credentials_never_printed():
    summary = credential_summary()
    dumped = str(summary)
    assert "credential_values_printed" in summary
    assert summary["credential_values_printed"] is False
    assert "HG_MOLTBOOK_TOKEN" not in dumped or "False" in dumped


def test_read_allowed_requires_present_token(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "test-token-not-printed")
    scope = check_credential_scope(LiveReadSurface.MOLTBOOK)
    assert scope.read_allowed is True
    assert scope.write_allowed is False
