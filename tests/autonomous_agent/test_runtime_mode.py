"""Runtime mode resolution tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.runtime_mode import (  # noqa: E402
    RuntimeMode,
    RuntimeModeError,
    resolve_runtime_mode,
)


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch):
    for key in (
        "HG_RUNTIME_MODE",
        "HG_ALLOW_FIXTURE_MODE",
        "HG_COGNITIVE_SOAK_ACTIVE",
        "HG_INFER_DRY_RUN",
        "HG_PROOF_REPLAY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_runtime_mode_is_not_fixture():
    receipt = resolve_runtime_mode()
    assert receipt.runtime_mode != RuntimeMode.FIXTURE
    assert receipt.runtime_mode == RuntimeMode.LOCAL_DEV
    assert receipt.fixture_allowed is False


def test_fixture_mode_requires_allow_env(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    with pytest.raises(RuntimeModeError):
        resolve_runtime_mode()


def test_fixture_mode_allowed_when_explicit(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    receipt = resolve_runtime_mode()
    assert receipt.runtime_mode == RuntimeMode.FIXTURE
    assert receipt.fixture_allowed is True
    assert receipt.source.value == "env"


def test_cognitive_soak_disallows_fixture(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    with pytest.raises(RuntimeModeError):
        resolve_runtime_mode()
