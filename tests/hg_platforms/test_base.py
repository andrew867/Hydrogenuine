"""Tests for hg_platforms.base."""

import os

import pytest

from hg_lib.errors import HydrogenuineError

from hg_platforms.base import PlatformError, require_not_dry_run


def test_require_not_dry_run_passes_when_not_set():
    require_not_dry_run("test_action")


def test_require_not_dry_run_raises_when_set(monkeypatch):
    monkeypatch.setenv("HG_DRY_RUN", "1")
    with pytest.raises(HydrogenuineError) as exc_info:
        require_not_dry_run("post")
    assert exc_info.value.code == "DRY_RUN_ACTIVE"


def test_platform_error_inherits_hg():
    err = PlatformError("Test error", code="TEST_CODE")
    assert isinstance(err, HydrogenuineError)
    assert err.code == "TEST_CODE"
