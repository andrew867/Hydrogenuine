"""Dry autonomous loop postflight tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopPostflightError
from hg_runtime.dry_autonomous_loop.loop_runner import run_bounded_dry_autonomous_loop
from hg_runtime.dry_autonomous_loop.postflight import run_loop_postflight
from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig, now_iso


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


def test_postflight_after_successful_run(tmp_path):
    result = run_bounded_dry_autonomous_loop(
        DryAutonomousLoopConfig(
            run_id="run-pf",
            agent_id="zero",
            schedule_mode="manual_step",
            max_iterations=1,
            turn_interval_seconds=0.0,
            created_at=now_iso(),
        ).with_hash(),
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
    )
    assert result.postflight_ref
    pf = run_loop_postflight(
        run_id="run-pf",
        agent_id="zero",
        started_at=result.started_at,
        iteration_count=result.iteration_count,
        loop_base=tmp_path / "loop",
        turn_base=tmp_path / "turns",
        boot_anchor={"local_committed": True, "journal_receipt_id": "test"},
        shutdown_anchor={"local_committed": True, "journal_receipt_id": "test"},
    )
    assert pf.replay_verdict == "GREEN_REPLAY_OK"
    assert pf.iteration_count == 1
    assert pf.lock_released
    assert pf.boot_anchor_committed
    assert pf.shutdown_anchor_committed


def test_postflight_detects_missing_journal(tmp_path):
    with pytest.raises(DryAutonomousLoopPostflightError):
        run_loop_postflight(
            run_id="missing",
            agent_id="zero",
            started_at=now_iso(),
            iteration_count=1,
            loop_base=tmp_path / "loop",
            turn_base=tmp_path / "turns",
        )
