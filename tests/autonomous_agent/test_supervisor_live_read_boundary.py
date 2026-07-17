"""Supervisor live read boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.schema import BoundedSoakProfile  # noqa: E402
from hg_runtime.bounded_soak.supervisor import _social_read_surface  # noqa: E402
from hg_runtime.social_capability.schema import SocialSurface  # noqa: E402


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)


def _profile(**kwargs) -> BoundedSoakProfile:
    defaults = dict(
        profile_id="test",
        duration_minutes=5,
        allow_live_social_read=True,
        allow_live_social_publish=False,
        max_posts=0,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    defaults.update(kwargs)
    return BoundedSoakProfile(**defaults)


def test_supervisor_does_not_force_fixture_in_local_dev():
    surface = _social_read_surface(_profile())
    assert surface != SocialSurface.FIXTURE


def test_supervisor_does_not_force_fixture_in_cognitive_mode(monkeypatch):
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    surface = _social_read_surface(_profile())
    assert surface != SocialSurface.FIXTURE


def test_supervisor_uses_moltbook_when_live_read_enabled(monkeypatch):
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_READ", "true")
    surface = _social_read_surface(_profile(allow_live_social_read=True))
    assert surface == SocialSurface.MOLTBOOK


def test_supervisor_fixture_only_in_explicit_fixture_mode(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    surface = _social_read_surface(_profile())
    assert surface == SocialSurface.FIXTURE
