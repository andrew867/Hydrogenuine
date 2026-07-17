"""INFER config dry-run boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_core.infer_live.config import (  # noqa: E402
    cognitive_soak_active,
    infer_dry_run_mode,
    provider_fallback_allowed,
)


@pytest.fixture(autouse=True)
def _clear_infer_env(monkeypatch):
    for key in ("HG_INFER_DRY_RUN", "HG_COGNITIVE_SOAK_ACTIVE", "HG_RUNTIME_MODE", "HG_ALLOW_FIXTURE_MODE"):
        monkeypatch.delenv(key, raising=False)


def test_infer_dry_run_not_hardcoded_true(monkeypatch):
    monkeypatch.setenv("HG_INFER_DRY_RUN", "0")
    assert infer_dry_run_mode() is False
    monkeypatch.setenv("HG_INFER_DRY_RUN", "1")
    assert infer_dry_run_mode() is True


def test_infer_dry_run_default_false_when_unset():
    assert infer_dry_run_mode() is False


def test_provider_fallback_not_real_cognition_in_cognitive_mode(monkeypatch):
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    assert cognitive_soak_active() is True
    assert provider_fallback_allowed() is False


def test_provider_fallback_allowed_in_fixture_mode(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    assert provider_fallback_allowed() is True
