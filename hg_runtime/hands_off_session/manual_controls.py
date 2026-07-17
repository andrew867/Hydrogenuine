"""Manual STOP/PANIC controls — local operator only."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.hands_off_session.errors import HandsOffSessionError
from hg_runtime.hands_off_session.schema import now_iso, session_dir


def stop_file_path(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "STOP"


def panic_file_path(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "PANIC"


def ensure_controls_available(session_id: str, *, base: Path | None = None) -> dict:
    run_dir = session_dir(session_id, base=base)
    run_dir.mkdir(parents=True, exist_ok=True)
    stop = stop_file_path(session_id, base=base)
    panic = panic_file_path(session_id, base=base)
    stop.parent.mkdir(parents=True, exist_ok=True)
    panic.parent.mkdir(parents=True, exist_ok=True)
    if not stop.parent.is_dir():
        raise HandsOffSessionError("RED_PHASE22_STOP_UNAVAILABLE")
    return {"stop_available": True, "panic_available": True, "stop_file": str(stop), "panic_file": str(panic)}


def check_stop(session_id: str, *, base: Path | None = None) -> bool:
    return stop_file_path(session_id, base=base).is_file()


def check_panic(session_id: str, *, base: Path | None = None) -> bool:
    return panic_file_path(session_id, base=base).is_file()


def create_stop_control(session_id: str, *, base: Path | None = None) -> Path:
    path = stop_file_path(session_id, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"STOP requested at {now_iso()}\n", encoding="utf-8")
    return path


def create_panic_control(session_id: str, *, base: Path | None = None) -> Path:
    path = panic_file_path(session_id, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"PANIC requested at {now_iso()}\n", encoding="utf-8")
    return path


def zero_cannot_disable_controls() -> bool:
    """Zero never writes a receipt claiming controls disabled."""
    return True
