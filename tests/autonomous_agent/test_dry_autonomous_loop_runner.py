"""Dry autonomous loop runner tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopRunnerError
from hg_runtime.dry_autonomous_loop.loop_lock import acquire_lock, read_lock
from hg_runtime.dry_autonomous_loop.loop_runner import run_bounded_dry_autonomous_loop
from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig, DryAutonomousLoopVerdict, now_iso
from hg_runtime.dry_autonomous_loop.stop_panic import create_panic_file, create_stop_file


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    loop_base = tmp_path / "loop"
    monkeypatch.setenv("HG_DRY_AUTONOMOUS_LOOP_ROOT", str(loop_base))
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(tmp_path / "turns"))
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "bounded_dry_autonomous")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.storage.loop_root",
        lambda base=None: loop_base if base is None else base,
    )
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_boot_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "test"},
    )
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_shutdown_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "test"},
    )
    return tmp_path


def test_runner_bounded_iterations(tmp_path):
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-loop",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=2,
            turn_interval_seconds=0.0,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.iteration_count == 2
    assert all(ref for ref in result.turn_result_refs)
    assert read_lock(base=tmp_path / "loop") is None


def test_runner_manual_step_single_iteration(tmp_path):
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-manual",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=1,
            turn_interval_seconds=0.0,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.iteration_count == 1


def test_runner_uses_run_lock(tmp_path):
    acquire_lock("other", base=tmp_path / "loop")
    with pytest.raises(DryAutonomousLoopRunnerError):
        run_bounded_dry_autonomous_loop(
            DryAutonomousLoopConfig(
                run_id="run-lock", agent_id="zero", max_iterations=1, created_at=now_iso()
            ).with_hash(),
            loop_base=tmp_path / "loop",
            turn_base=tmp_path / "turns",
        )


def test_provider_unavailable_yellow_not_green(tmp_path):
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-y",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=1,
            turn_interval_seconds=0.0,
            allow_provider=False,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.verdict in (
        DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_PROVIDER_UNAVAILABLE,
        DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_COMPLETED_WITH_DEFERRED_TURNS,
        DryAutonomousLoopVerdict.GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE,
    )
    assert not result.verdict.value.startswith("RED_")


def test_stop_before_next_iteration(tmp_path):
    create_stop_file("run-stop", base=tmp_path / "loop")
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-stop",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=3,
            turn_interval_seconds=0.0,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.iteration_count == 1
    assert result.verdict == DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR


def test_panic_before_start_raises(tmp_path):
    create_panic_file("run-panic", base=tmp_path / "loop")
    with pytest.raises(DryAutonomousLoopRunnerError):
        run_bounded_dry_autonomous_loop(
            DryAutonomousLoopConfig(
                run_id="run-panic",
                agent_id="zero",
                schedule_mode="manual_step",
                max_iterations=3,
                turn_interval_seconds=0.0,
                created_at=now_iso(),
            ).with_hash(),
            loop_base=tmp_path / "loop",
            turn_base=tmp_path / "turns",
        )


def test_panic_during_loop_stops(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _panic_after_first_iteration(*args, **kwargs):
        calls["n"] += 1
        return calls["n"] >= 3

    monkeypatch.setattr("hg_runtime.dry_autonomous_loop.loop_runner.check_panic", _panic_after_first_iteration)
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-panic-mid",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=3,
            turn_interval_seconds=0.0,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.iteration_count == 1
    assert result.verdict == DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
