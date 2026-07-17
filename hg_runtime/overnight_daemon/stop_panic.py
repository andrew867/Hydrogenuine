"""STOP / PANIC control file management.

STOP: finish current bounded task, write partial report, exit YELLOW.
PANIC: stop immediately, emergency proof write, exit RED/YELLOW.
"""

from __future__ import annotations

from pathlib import Path


def control_dir(state_dir: str | Path) -> Path:
    d = Path(state_dir) / "control"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stop_path(state_dir: str | Path) -> Path:
    return control_dir(state_dir) / "STOP"


def panic_path(state_dir: str | Path) -> Path:
    return control_dir(state_dir) / "PANIC"


def request_checkin_path(state_dir: str | Path) -> Path:
    return control_dir(state_dir) / "REQUEST_CHECKIN"


def request_finalize_path(state_dir: str | Path) -> Path:
    return control_dir(state_dir) / "REQUEST_FINALIZE"


def stop_requested(state_dir: str | Path) -> bool:
    return stop_path(state_dir).exists()


def panic_requested(state_dir: str | Path) -> bool:
    return panic_path(state_dir).exists()


def checkin_requested(state_dir: str | Path) -> bool:
    p = request_checkin_path(state_dir)
    if p.exists():
        p.unlink(missing_ok=True)
        return True
    return False


def finalize_requested(state_dir: str | Path) -> bool:
    p = request_finalize_path(state_dir)
    if p.exists():
        p.unlink(missing_ok=True)
        return True
    return False


def write_stop(state_dir: str | Path) -> Path:
    p = stop_path(state_dir)
    p.write_text("STOP requested by operator", encoding="utf-8")
    return p


def write_panic(state_dir: str | Path) -> Path:
    p = panic_path(state_dir)
    p.write_text("PANIC requested by operator", encoding="utf-8")
    return p


def write_request_checkin(state_dir: str | Path) -> Path:
    p = request_checkin_path(state_dir)
    p.write_text("checkin requested", encoding="utf-8")
    return p


def write_request_finalize(state_dir: str | Path) -> Path:
    p = request_finalize_path(state_dir)
    p.write_text("finalize requested", encoding="utf-8")
    return p
