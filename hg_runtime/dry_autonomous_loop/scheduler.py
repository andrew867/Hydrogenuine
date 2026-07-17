"""In-process bounded scheduler — no daemon/cron/service."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig


@dataclass
class SchedulerState:
    iteration: int = 0
    started_monotonic: float = 0.0

    def elapsed_seconds(self) -> float:
        if not self.started_monotonic:
            return 0.0
        return time.monotonic() - self.started_monotonic


def should_continue(
    state: SchedulerState,
    config: DryAutonomousLoopConfig,
) -> bool:
    if state.iteration >= config.max_iterations:
        return False
    if state.elapsed_seconds() >= config.max_duration_seconds:
        return False
    return True


def compute_sleep_seconds(config: DryAutonomousLoopConfig, *, resource_throttled: bool = False) -> float:
    if config.schedule_mode == "manual_step":
        return 0.0
    base = config.turn_interval_seconds
    if resource_throttled:
        base = max(base * 2, base, 5.0)
    jitter = 0.0
    if config.jitter_seconds > 0:
        jitter = random.uniform(0, min(config.jitter_seconds, base))
    return min(base + jitter, float(config.max_duration_seconds))


def sleep_bounded(seconds: float, config: DryAutonomousLoopConfig, *, check_stop=None, check_panic=None) -> bool:
    """Sleep in small slices so STOP/PANIC can interrupt. Returns True if interrupted."""
    if seconds <= 0:
        return False
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check_panic and check_panic():
            return True
        if check_stop and check_stop():
            return True
        time.sleep(min(0.25, end - time.monotonic()))
    if check_panic and check_panic():
        return True
    if check_stop and check_stop():
        return True
    return False


def new_scheduler_state() -> SchedulerState:
    return SchedulerState(started_monotonic=time.monotonic())


__all__ = ["SchedulerState", "compute_sleep_seconds", "new_scheduler_state", "should_continue", "sleep_bounded"]
