"""Extended dry autonomy runner tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyRunnerError
from hg_runtime.extended_dry_autonomy.extended_lock import acquire_lock, read_lock
from hg_runtime.extended_dry_autonomy.extended_runner import run_extended_dry_autonomy
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyConfig, ExtendedDryAutonomyVerdict, now_iso
from hg_runtime.dry_autonomous_loop.stop_panic import create_stop_file


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    ext = tmp_path / "ext"
    turns = tmp_path / "turns"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(turns))
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "extended_dry_autonomy")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_boot_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "boot"},
    )
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_shutdown_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "stop"},
    )
    return ext, turns


def _cfg(run_id: str, **kwargs) -> ExtendedDryAutonomyConfig:
    base = dict(
        run_id=run_id,
        agent_id="zero",
        max_iterations=2,
        max_duration_seconds=300,
        turn_interval_seconds=0.0,
        checkpoint_every_iterations=1,
        created_at=now_iso(),
    )
    base.update(kwargs)
    return ExtendedDryAutonomyConfig(**base).with_hash()


def test_runner_bounded_iterations(_env):
    ext, turns = _env
    result = run_extended_dry_autonomy(_cfg("run-bounded"), extended_base=ext, turn_base=turns)
    assert result.iteration_count == 2
    assert len(result.turn_result_refs) == 2
    assert read_lock(base=ext) is None


def test_runner_uses_run_lock(_env):
    ext, turns = _env
    acquire_lock("other", base=ext)
    with pytest.raises(ExtendedDryAutonomyRunnerError):
        run_extended_dry_autonomy(_cfg("run-lock"), extended_base=ext, turn_base=turns)


def test_provider_unavailable_yellow(_env):
    ext, turns = _env
    result = run_extended_dry_autonomy(
        _cfg("run-y", allow_provider=False, max_iterations=1),
        extended_base=ext,
        turn_base=turns,
    )
    assert result.verdict == ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_PROVIDER_UNAVAILABLE


def test_stop_by_operator(_env):
    ext, turns = _env
    import threading
    import time

    def _stop_later():
        time.sleep(0.5)
        create_stop_file("run-stop", stop_path=str(ext / "run-stop" / "STOP"))

    threading.Thread(target=_stop_later, daemon=True).start()
    result = run_extended_dry_autonomy(
        _cfg("run-stop", max_iterations=10, turn_interval_seconds=5.0),
        extended_base=ext,
        turn_base=turns,
    )
    assert result.verdict == ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
