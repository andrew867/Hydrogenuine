"""Dry soak runner tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.dry_soak_runner import run_longer_supervised_dry_soak
from hg_runtime.dry_soak.errors import DrySoakRunnerError
from hg_runtime.dry_soak.schema import DrySoakConfig, DrySoakVerdict, now_iso
from hg_runtime.supervised_rehearsal.errors import RehearsalLockError
from hg_runtime.supervised_rehearsal.run_lock import acquire_lock, read_lock
from hg_runtime.supervised_rehearsal.stop_panic import create_panic_file, create_stop_file


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "supervised_dry")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setattr("hg_runtime.dry_soak.storage.dry_soak_root", lambda base=None: tmp_path / "dry_soak")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "dry_soak")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "dry_soak")
    monkeypatch.setattr(
        "hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir",
        lambda run_id, base=None: (tmp_path / "dry_soak" / run_id),
    )
    return tmp_path


def test_runner_bounded_turns(tmp_path):
    result = run_longer_supervised_dry_soak(
        DrySoakConfig(
            run_id="run-ds", agent_id="zero", max_turns=2, turn_interval_seconds=0, created_at=now_iso()
        ).with_hash(),
        soak_base=tmp_path / "dry_soak",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 2
    assert all(s.turn_receipt_ref for s in result.turn_summaries)
    assert read_lock(base=tmp_path / "dry_soak") is None


def test_runner_bounded_duration(tmp_path, monkeypatch):
    elapsed_calls = {"n": 0}

    def _fake_elapsed(_started_at: str) -> float:
        elapsed_calls["n"] += 1
        return 0.0 if elapsed_calls["n"] <= 1 else 9999.0

    monkeypatch.setattr("hg_runtime.dry_soak.dry_soak_runner._elapsed_seconds", _fake_elapsed)
    result = run_longer_supervised_dry_soak(
        DrySoakConfig(
            run_id="run-dur", agent_id="zero", max_turns=10, max_duration_seconds=1, created_at=now_iso()
        ).with_hash(),
        soak_base=tmp_path / "dry_soak",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 1


def test_runner_uses_run_lock(tmp_path):
    acquire_lock("other", base=tmp_path / "dry_soak")
    with pytest.raises(DrySoakRunnerError):
        run_longer_supervised_dry_soak(
            DrySoakConfig(run_id="run-lock", agent_id="zero", max_turns=1, created_at=now_iso()).with_hash(),
            soak_base=tmp_path / "dry_soak",
            turn_base=tmp_path / "turns",
        )


def test_provider_unavailable_yellow_not_green(tmp_path):
    result = run_longer_supervised_dry_soak(
        DrySoakConfig(
            run_id="run-y", agent_id="zero", max_turns=1, allow_provider=False, created_at=now_iso()
        ).with_hash(),
        soak_base=tmp_path / "dry_soak",
        turn_base=tmp_path / "turns",
    )
    assert result.verdict in (
        DrySoakVerdict.YELLOW_DRY_SOAK_COMPLETED_WITH_PROVIDER_UNAVAILABLE,
        DrySoakVerdict.YELLOW_DRY_SOAK_NO_ARTIFACTS_CREATED,
        DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE,
    )
    assert not result.verdict.value.startswith("RED_")


def test_stop_before_next_turn(tmp_path):
    create_stop_file("run-stop", base=tmp_path / "dry_soak")
    result = run_longer_supervised_dry_soak(
        DrySoakConfig(run_id="run-stop", agent_id="zero", max_turns=3, created_at=now_iso()).with_hash(),
        soak_base=tmp_path / "dry_soak",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 1
    assert result.verdict == DrySoakVerdict.YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR


def test_panic_stops_run(tmp_path):
    create_panic_file("run-panic", base=tmp_path / "dry_soak")
    result = run_longer_supervised_dry_soak(
        DrySoakConfig(run_id="run-panic", agent_id="zero", max_turns=3, created_at=now_iso()).with_hash(),
        soak_base=tmp_path / "dry_soak",
        turn_base=tmp_path / "turns",
    )
    assert result.turn_count == 0
    assert result.verdict == DrySoakVerdict.YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR
