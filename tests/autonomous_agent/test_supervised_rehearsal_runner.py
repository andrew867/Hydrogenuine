"""Supervised rehearsal runner tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.supervised_rehearsal.rehearsal_runner import run_supervised_rehearsal
from hg_runtime.supervised_rehearsal.run_lock import read_lock
from hg_runtime.supervised_rehearsal.schema import SupervisedRehearsalConfig, SupervisedRehearsalVerdict, now_iso
from hg_runtime.supervised_rehearsal.stop_panic import create_panic_file, create_stop_file


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir", lambda run_id, base=None: (tmp_path / "rehearsals" / run_id))
    return tmp_path


def test_runner_bounded_turns(tmp_path):
    result = run_supervised_rehearsal(
        SupervisedRehearsalConfig(
            run_id="run-rr", agent_id="zero", max_turns=2, turn_interval_seconds=0, created_at=now_iso()
        ).with_hash(),
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 2
    assert len(result.turn_summaries) == 2
    assert all(s.turn_receipt_ref for s in result.turn_summaries)
    assert read_lock(base=tmp_path / "rehearsals") is None


def test_provider_unavailable_yellow_not_green(tmp_path):
    result = run_supervised_rehearsal(
        SupervisedRehearsalConfig(
            run_id="run-y", agent_id="zero", max_turns=1, allow_provider=False, created_at=now_iso()
        ).with_hash(),
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert result.verdict in (
        SupervisedRehearsalVerdict.YELLOW_REHEARSAL_PROVIDER_UNAVAILABLE,
        SupervisedRehearsalVerdict.YELLOW_REHEARSAL_COMPLETED_WITH_DEFERRED_TURNS,
        SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE,
    )
    assert not result.verdict.value.startswith("RED_")


def test_stop_before_next_turn(tmp_path):
    create_stop_file("run-stop", base=tmp_path / "rehearsals")
    result = run_supervised_rehearsal(
        SupervisedRehearsalConfig(
            run_id="run-stop", agent_id="zero", max_turns=3, created_at=now_iso()
        ).with_hash(),
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 1
    assert result.verdict == SupervisedRehearsalVerdict.YELLOW_REHEARSAL_STOPPED_BY_OPERATOR


def test_panic_stops_run(tmp_path):
    create_panic_file("run-panic", base=tmp_path / "rehearsals")
    result = run_supervised_rehearsal(
        SupervisedRehearsalConfig(
            run_id="run-panic", agent_id="zero", max_turns=3, created_at=now_iso()
        ).with_hash(),
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 0
    assert result.verdict == SupervisedRehearsalVerdict.YELLOW_REHEARSAL_STOPPED_BY_OPERATOR
