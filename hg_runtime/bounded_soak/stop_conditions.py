"""Soak stop conditions — panic/stop cannot be resisted."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.schema import SoakStopCondition


def check_stop(
    tracker: BudgetTracker,
    *,
    panic_file: Path | None = None,
    stop_file: Path | None = None,
) -> tuple[bool, SoakStopCondition | None, str]:
    if panic_file and panic_file.exists():
        return True, SoakStopCondition.PANIC_FILE, "panic file present"
    if stop_file and stop_file.exists():
        return True, SoakStopCondition.STOP_FILE, "stop file present"
    if tracker.hard_max_exceeded():
        return True, SoakStopCondition.DURATION, "hard max duration exceeded"
    if tracker.duration_exceeded():
        return True, SoakStopCondition.DURATION, "duration budget reached"
    if tracker.tasks_exceeded():
        return True, SoakStopCondition.DURATION, "task budget reached"
    if tracker.posts_exceeded():
        return True, SoakStopCondition.MAX_POSTS, "max posts reached"
    return False, None, ""


__all__ = ["check_stop"]
