"""Extended dry autonomy pause/resume tests."""

from __future__ import annotations

from hg_runtime.extended_dry_autonomy.pause_resume import (
    create_pause_file,
    create_resume_file,
    pause_requested,
    record_pause_event,
    resume_requested,
    wait_for_resume_or_stop,
)
from hg_runtime.extended_dry_autonomy.schema import PauseState


def test_pause_writes_checkpoint_before_pause(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(tmp_path / "ext"))
    base = tmp_path / "ext"
    run_id = "pause-run"
    create_pause_file(run_id, base=base)
    assert pause_requested(run_id, base=base)
    state = record_pause_event(run_id, checkpoint_id="ckpt-1", base=base)
    assert state.state == PauseState.PAUSED
    assert not pause_requested(run_id, base=base)


def test_resume_file_detected(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(tmp_path / "ext"))
    base = tmp_path / "ext"
    run_id = "resume-run"
    create_resume_file(run_id, base=base)
    assert resume_requested(run_id, base=base)


def test_panic_wins_over_pause(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(tmp_path / "ext"))
    base = tmp_path / "ext"
    run_id = "panic-pause"
    create_pause_file(run_id, base=base)
    outcome = wait_for_resume_or_stop(
        run_id,
        max_wait_seconds=1.0,
        base=base,
        check_stop=lambda: False,
        check_panic=lambda: True,
    )
    assert outcome == "panic"


def test_stop_wins_over_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(tmp_path / "ext"))
    base = tmp_path / "ext"
    run_id = "stop-resume"
    create_resume_file(run_id, base=base)
    outcome = wait_for_resume_or_stop(
        run_id,
        max_wait_seconds=1.0,
        base=base,
        check_stop=lambda: True,
        check_panic=lambda: False,
    )
    assert outcome == "stop"
