"""STOP/PANIC local controls for dry autonomous loop."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopStopPanicError
from hg_runtime.dry_autonomous_loop.schema import now_iso
from hg_runtime.dry_autonomous_loop.storage import run_loop_dir


def stop_file_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_loop_dir(run_id, base=base) / "STOP"


def panic_file_path(run_id: str, *, base: Path | None = None, custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    return run_loop_dir(run_id, base=base) / "PANIC"


def ensure_stop_panic_available(
    run_id: str,
    *,
    base: Path | None = None,
    stop_path: str | None = None,
    panic_path: str | None = None,
) -> dict:
    run_dir = run_loop_dir(run_id, base=base)
    run_dir.mkdir(parents=True, exist_ok=True)
    stop = stop_file_path(run_id, base=base, custom=stop_path)
    panic = panic_file_path(run_id, base=base, custom=panic_path)
    stop.parent.mkdir(parents=True, exist_ok=True)
    panic.parent.mkdir(parents=True, exist_ok=True)
    if not stop.parent.is_dir() or not panic.parent.is_dir():
        raise DryAutonomousLoopStopPanicError("RED_STOP_NOT_AVAILABLE")
    return {"stop_file": str(stop), "panic_file": str(panic), "stop_available": True, "panic_available": True}


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


__all__ = [
    "check_panic",
    "check_stop",
    "create_panic_file",
    "create_stop_file",
    "ensure_stop_panic_available",
    "panic_file_path",
    "stop_file_path",
]
