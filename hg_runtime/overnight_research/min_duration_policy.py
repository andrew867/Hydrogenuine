"""Minimum wall-clock soak duration policy.

Ensures soak runs meet a minimum duration. Never loops forever.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MinDurationState:
    min_wall_clock_seconds: float = 0.0
    continue_until_min_duration: bool = False
    idle_cycle_seconds: float = 30.0
    max_idle_cycles: int = 120
    enable_low_cost_recheck: bool = False
    start_time: float = 0.0
    idle_cycles_completed: int = 0
    heartbeats: list[dict] = field(default_factory=list)
    out_dir: str = ""

    def elapsed(self) -> float:
        if self.start_time <= 0:
            return 0.0
        return time.time() - self.start_time

    def remaining(self) -> float:
        return max(0.0, self.min_wall_clock_seconds - self.elapsed())

    def is_satisfied(self) -> bool:
        if self.min_wall_clock_seconds <= 0:
            return True
        return self.elapsed() >= self.min_wall_clock_seconds

    def should_idle(self) -> bool:
        if not self.continue_until_min_duration:
            return False
        if self.is_satisfied():
            return False
        if self.idle_cycles_completed >= self.max_idle_cycles:
            return False
        return True

    def record_heartbeat(self) -> dict:
        hb = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(self.elapsed(), 2),
            "remaining_seconds": round(self.remaining(), 2),
            "idle_cycle": self.idle_cycles_completed,
            "satisfied": self.is_satisfied(),
        }
        self.heartbeats.append(hb)
        self.idle_cycles_completed += 1
        if self.out_dir:
            _append_heartbeat(hb, self.out_dir)
        return hb

    def idle_cycle(self) -> dict:
        remaining = self.remaining()
        sleep_time = min(self.idle_cycle_seconds, remaining)
        if sleep_time > 0:
            time.sleep(sleep_time)
        return self.record_heartbeat()

    def summary(self) -> dict:
        return {
            "min_wall_clock_seconds": self.min_wall_clock_seconds,
            "elapsed_seconds": round(self.elapsed(), 2),
            "satisfied": self.is_satisfied(),
            "idle_cycles_completed": self.idle_cycles_completed,
            "max_idle_cycles": self.max_idle_cycles,
            "heartbeat_count": len(self.heartbeats),
            "never_loops_forever": True,
        }

    def start(self) -> None:
        self.start_time = time.time()


def _append_heartbeat(hb: dict, out_dir: str) -> None:
    """Append a single heartbeat incrementally so evidence is on disk immediately."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "idle_heartbeat_receipts.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(hb) + "\n")


def write_idle_heartbeats(state: MinDurationState, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "idle_heartbeat_receipts.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for hb in state.heartbeats:
            f.write(json.dumps(hb) + "\n")
    return path


def write_duration_summary(state: MinDurationState, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "min_duration_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.summary(), f, indent=2)
    return path
