"""Bounded soak active run tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.bounded_soak.active_run import assess_active_run, apply_active_run_decision
from hg_runtime.bounded_soak.supervisor_lock import acquire_supervisor_lock
from hg_runtime.bounded_soak.stop_panic_runtime import may_start_supervisor, write_stop_receipt


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "run"
    rd.mkdir()
    (rd / "command_log.jsonl").write_text(
        json.dumps({"event": "SOAK_START", "ts": "2026-06-16T03:00:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    (rd / "run_control.json").write_text(
        json.dumps({"allow_live_social_publish": True}) + "\n",
        encoding="utf-8",
    )
    return rd


def test_active_run_red_without_observer(run_dir: Path, tmp_path: Path):
    assessment = assess_active_run(workspace=tmp_path, run_dir=run_dir)
    assert assessment["active"]
    assert assessment["verdict"] == "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER"


def test_pause_publish_decision(run_dir: Path, tmp_path: Path):
    result = apply_active_run_decision("pause_publish", run_dir=run_dir, workspace=tmp_path)
    assert result["ok"]


def test_supervisor_lock_denies_duplicate(run_dir: Path, tmp_path: Path):
    ok1, _, _ = acquire_supervisor_lock(run_dir, supervisor_id="a", workspace=tmp_path)
    ok2, reason, _ = acquire_supervisor_lock(run_dir, supervisor_id="b", workspace=tmp_path)
    assert ok1
    assert not ok2
    assert "RED_MULTIPLE_SUPERVISORS" in reason


def test_stop_blocks_supervisor_restart(tmp_path: Path):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "STOP").write_text("1\n")
    ok, reason = may_start_supervisor(tmp_path)
    assert not ok
    assert "stop" in reason.lower()


def test_stop_receipt_written(tmp_path: Path, run_dir: Path):
    ref = write_stop_receipt(tmp_path, run_dir=run_dir)
    assert ref
    assert (tmp_path / ".hg-local" / "soak" / "stop_panic_receipts.jsonl").is_file()
