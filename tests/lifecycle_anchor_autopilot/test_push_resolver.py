"""Tests for lifecycle anchor push policy resolution."""

from __future__ import annotations

import os

import pytest

from hg_runtime.lifecycle_anchor_autopilot.push_resolver import resolve_lifecycle_push_policy
import shutil

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


@pytest.fixture(autouse=True)
def _clear_push_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("HG_ANCHOR_ALLOW_PUSH", "HG_LIFECYCLE_AUTOPUSH_ENABLED"):
        monkeypatch.delenv(key, raising=False)


@_requires_gh
def test_config_and_credentials_enable_push_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = resolve_lifecycle_push_policy()
    assert policy.config_allow_push is True
    if policy.credentials_ok:
        assert policy.push_requested is True
        assert policy.lifecycle_autopush_enabled is True
        assert policy.dry_run is False
        assert policy.verdict == "GREEN_LIFECYCLE_ANCHOR_AUTOPUSH_READY"


@_requires_gh
def test_explicit_env_false_blocks_push(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_ANCHOR_ALLOW_PUSH", "false")
    policy = resolve_lifecycle_push_policy()
    assert policy.push_requested is False
    assert policy.dry_run is True
    assert policy.verdict == "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"


@_requires_gh
def test_autopush_env_false_blocks_push(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_LIFECYCLE_AUTOPUSH_ENABLED", "false")
    policy = resolve_lifecycle_push_policy()
    assert policy.push_requested is False
    assert policy.lifecycle_autopush_enabled is False


@_requires_gh
def test_payload_has_no_secrets() -> None:
    payload = resolve_lifecycle_push_policy().to_payload()
    blob = str(payload).lower()
    assert "ghp_" not in blob
    assert "private_key" not in blob
