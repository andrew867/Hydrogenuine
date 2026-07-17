"""Extended dry autonomy pause/resume — local operator controls only."""

from __future__ import annotations

import json
import time
from pathlib import Path

from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyPauseResumeError
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyPauseState, PauseState, now_iso
from hg_runtime.extended_dry_autonomy.storage import run_dir, write_json


def default_pause_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_dir(run_id, base=base) / "PAUSE"


def default_resume_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_dir(run_id, base=base) / "RESUME"


def pause_requested(run_id: str, *, base: Path | None = None, pause_path: str | None = None) -> bool:
    return default_pause_path(run_id, base=base, custom=pause_path).is_file()


def resume_requested(run_id: str, *, base: Path | None = None, resume_path: str | None = None) -> bool:
    return default_resume_path(run_id, base=base, custom=resume_path).is_file()


def create_pause_file(run_id: str, *, base: Path | None = None, pause_path: str | None = None) -> Path:
    path = default_pause_path(run_id, base=base, custom=pause_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(now_iso() + "\n", encoding="utf-8")
    return path


def create_resume_file(run_id: str, *, base: Path | None = None, resume_path: str | None = None) -> Path:
    path = default_resume_path(run_id, base=base, custom=resume_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(now_iso() + "\n", encoding="utf-8")
    return path


def clear_pause_file(run_id: str, *, base: Path | None = None, pause_path: str | None = None) -> None:
    default_pause_path(run_id, base=base, custom=pause_path).unlink(missing_ok=True)


def clear_resume_file(run_id: str, *, base: Path | None = None, resume_path: str | None = None) -> None:
    default_resume_path(run_id, base=base, custom=resume_path).unlink(missing_ok=True)


def load_pause_state(run_id: str, *, base: Path | None = None) -> ExtendedDryAutonomyPauseState | None:
    path = run_dir(run_id, base=base) / "pause_state.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExtendedDryAutonomyPauseState(
        run_id=data["run_id"],
        state=PauseState(data["state"]),
        paused_at=data.get("paused_at"),
        resumed_at=data.get("resumed_at"),
        checkpoint_id=data.get("checkpoint_id"),
        events=data.get("events", []),
    )


def save_pause_state(state: ExtendedDryAutonomyPauseState, *, base: Path | None = None) -> Path:
    return write_json(run_dir(state.run_id, base=base) / "pause_state.json", state.to_payload())


def record_pause_event(
    run_id: str,
    *,
    checkpoint_id: str,
    base: Path | None = None,
    pause_path: str | None = None,
) -> ExtendedDryAutonomyPauseState:
    existing = load_pause_state(run_id, base=base) or ExtendedDryAutonomyPauseState(
        run_id=run_id, state=PauseState.RUNNING
    )
    ts = now_iso()
    existing.state = PauseState.PAUSED
    existing.paused_at = ts
    existing.checkpoint_id = checkpoint_id
    existing.events.append({"kind": "pause", "at": ts, "checkpoint_id": checkpoint_id})
    save_pause_state(existing, base=base)
    clear_pause_file(run_id, base=base, pause_path=pause_path)
    return existing


def record_resume_event(
    run_id: str,
    *,
    checkpoint_id: str,
    base: Path | None = None,
    resume_path: str | None = None,
) -> ExtendedDryAutonomyPauseState:
    existing = load_pause_state(run_id, base=base)
    if not existing:
        raise ExtendedDryAutonomyPauseResumeError("RED_EXTENDED_DRY_AUTONOMY_RESUME_FAILURE:no_pause_state")
    ts = now_iso()
    existing.state = PauseState.RESUMED
    existing.resumed_at = ts
    existing.checkpoint_id = checkpoint_id
    existing.events.append({"kind": "resume", "at": ts, "checkpoint_id": checkpoint_id})
    save_pause_state(existing, base=base)
    clear_resume_file(run_id, base=base, resume_path=resume_path)
    return existing


def wait_for_resume_or_stop(
    run_id: str,
    *,
    max_wait_seconds: float = 300.0,
    base: Path | None = None,
    pause_path: str | None = None,
    resume_path: str | None = None,
    check_stop,
    check_panic,
) -> str:
    """Returns resume|stop|panic|timeout."""
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        if check_panic():
            return "panic"
        if check_stop():
            return "stop"
        if resume_requested(run_id, base=base, resume_path=resume_path):
            return "resume"
        time.sleep(0.5)
    return "timeout"


__all__ = [
    "clear_pause_file",
    "clear_resume_file",
    "create_pause_file",
    "create_resume_file",
    "default_pause_path",
    "default_resume_path",
    "load_pause_state",
    "pause_requested",
    "record_pause_event",
    "record_resume_event",
    "resume_requested",
    "save_pause_state",
    "wait_for_resume_or_stop",
]
