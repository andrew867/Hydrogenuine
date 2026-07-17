"""Stop/panic policy integration for operator queue."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class StopPanicState:
    stop_active: bool = False
    panic_active: bool = False
    emergency_lock: bool = False
    degraded_mode: bool = False

    def blocks_approval(self) -> bool:
        return self.stop_active or self.panic_active or self.emergency_lock

    def blocks_execution(self) -> bool:
        return self.panic_active or self.emergency_lock

    def to_payload(self) -> dict:
        return {
            "stop_active": self.stop_active,
            "panic_active": self.panic_active,
            "emergency_lock": self.emergency_lock,
            "degraded_mode": self.degraded_mode,
        }


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_stop_panic_state(
    workspace: Path | None = None,
    *,
    run_dir: Path | None = None,
) -> StopPanicState:
    ws = workspace or WORKSPACE
    soak_root = ws / ".hg-local" / "soak"
    stop_active = (soak_root / "STOP").is_file()
    panic_active = (soak_root / "PANIC").is_file()
    emergency_lock = False
    degraded_mode = False

    if run_dir and run_dir.is_dir():
        control = _read_json(run_dir / "run_control.json") or {}
        if control.get("emergency_lock"):
            emergency_lock = True
        if control.get("degraded_mode"):
            degraded_mode = True
        if control.get("stop_active"):
            stop_active = True
        if control.get("panic_active"):
            panic_active = True

    global_control = _read_json(soak_root / "control_state.json") or {}
    if global_control.get("emergency_lock"):
        emergency_lock = True
    if global_control.get("degraded_mode"):
        degraded_mode = True

    return StopPanicState(
        stop_active=stop_active,
        panic_active=panic_active,
        emergency_lock=emergency_lock,
        degraded_mode=degraded_mode,
    )


__all__ = ["StopPanicState", "load_stop_panic_state"]
