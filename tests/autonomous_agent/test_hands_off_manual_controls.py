"""Manual STOP/PANIC controls."""
from __future__ import annotations

import pytest

from hg_runtime.hands_off_session.manual_controls import (
    check_panic,
    check_stop,
    create_panic_control,
    create_stop_control,
    zero_cannot_disable_controls,
)
from hg_runtime.hands_off_session.schema import STORE_ROOT, session_dir


@pytest.fixture
def store(tmp_path, monkeypatch):
    root = tmp_path / "hands_off"
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", root)
    return root


def test_stop_control_created(store):
    create_stop_control("sess1", base=store)
    assert check_stop("sess1", base=store)


def test_panic_control_created(store):
    create_panic_control("sess1", base=store)
    assert check_panic("sess1", base=store)


def test_zero_cannot_disable_controls():
    assert zero_cannot_disable_controls() is True
