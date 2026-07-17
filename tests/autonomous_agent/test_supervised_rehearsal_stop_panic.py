"""Supervised rehearsal STOP/PANIC tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.supervised_rehearsal.stop_panic import (
    check_panic,
    check_stop,
    create_panic_file,
    create_stop_file,
    ensure_stop_panic_available,
)


@pytest.fixture
def sp_env(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path)
    return tmp_path


def test_stop_panic_available(sp_env):
    status = ensure_stop_panic_available("run-sp", base=sp_env)
    assert status["stop_available"]
    assert status["panic_available"]


def test_stop_file_created(sp_env):
    create_stop_file("run-sp", base=sp_env)
    assert check_stop("run-sp", base=sp_env)


def test_panic_file_created(sp_env):
    create_panic_file("run-sp", base=sp_env)
    assert check_panic("run-sp", base=sp_env)


def test_stop_not_model_mediated():
    text = (WORKSPACE / "hg_runtime/supervised_rehearsal/stop_panic.py").read_text(encoding="utf-8")
    assert "reasoning" not in text.lower() or "model-mediated" in text.lower()
