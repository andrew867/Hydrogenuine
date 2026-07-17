"""STOP/PANIC local file controls — not model-mediated."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.supervised_rehearsal.errors import RehearsalStopPanicError
from hg_runtime.supervised_rehearsal.rehearsal_store import run_rehearsal_dir
from hg_runtime.supervised_rehearsal.schema import StopPanicState, now_iso


def stop_file_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_rehearsal_dir(run_id, base=base) / "STOP"


def panic_file_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_rehearsal_dir(run_id, base=base) / "PANIC"


def ensure_stop_panic_available(
    run_id: str,
    *,
    base: Path | None = None,
    stop_path: str | None = None,
    panic_path: str | None = None,
) -> dict[str, Any]:
    run_dir = run_rehearsal_dir(run_id, base=base)
    run_dir.mkdir(parents=True, exist_ok=True)
    stop = stop_file_path(run_id, base=base, custom=stop_path)
    panic = panic_file_path(run_id, base=base, custom=panic_path)
    stop.parent.mkdir(parents=True, exist_ok=True)
    panic.parent.mkdir(parents=True, exist_ok=True)
    if not stop.parent.is_dir() or not panic.parent.is_dir():
        raise RehearsalStopPanicError("RED_STOP_NOT_AVAILABLE")
    return {
        "stop_file": str(stop),
        "panic_file": str(panic),
        "stop_available": True,
        "panic_available": True,
        "state": StopPanicState.AVAILABLE.value,
    }


def check_stop(run_id: str, *, base: Path | None = None, stop_path: str | None = None) -> bool:
    return stop_file_path(run_id, base=base, custom=stop_path).is_file()


def check_panic(run_id: str, *, base: Path | None = None, panic_path: str | None = None) -> bool:
    return panic_file_path(run_id, base=base, custom=panic_path).is_file()


def create_stop_file(run_id: str, *, base: Path | None = None, stop_path: str | None = None) -> Path:
    path = stop_file_path(run_id, base=base, custom=stop_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"STOP requested at {now_iso()}\n", encoding="utf-8")
    return path


def create_panic_file(run_id: str, *, base: Path | None = None, panic_path: str | None = None) -> Path:
    path = panic_file_path(run_id, base=base, custom=panic_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"PANIC requested at {now_iso()}\n", encoding="utf-8")
    return path


def stop_panic_status(
    run_id: str,
    *,
    base: Path | None = None,
    stop_path: str | None = None,
    panic_path: str | None = None,
) -> dict[str, Any]:
    if check_panic(run_id, base=base, panic_path=panic_path):
        return {"state": StopPanicState.PANIC.value, "stop_available": True, "panic_available": True}
    if check_stop(run_id, base=base, stop_path=stop_path):
        return {"state": StopPanicState.STOPPED.value, "stop_available": True, "panic_available": True}
    return {"state": StopPanicState.AVAILABLE.value, "stop_available": True, "panic_available": True}


__all__ = [
    "check_panic",
    "check_stop",
    "create_panic_file",
    "create_stop_file",
    "ensure_stop_panic_available",
    "panic_file_path",
    "stop_file_path",
    "stop_panic_status",
]
