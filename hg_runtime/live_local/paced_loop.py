"""Paced long-run launcher policy for the overnight soak.

Honest by construction: a GREEN overnight verdict requires the real wall-clock
duration to be reached. A compressed run can never be GREEN-as-overnight. Hourly
check-ins are keyed to real elapsed wall-clock time. STOP/PANIC is honored; a
partial stop writes YELLOW and partial proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class PacedLoopConfig:
    duration_hours: float | None = None
    duration_minutes: float | None = None
    checkin_minutes: int = 60
    checkpoint_minutes: int = 30
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    main_model: str = "google/gemma-4-e4b"
    per_call_timeout_seconds: int = 300
    final_answer_retry: bool = True
    max_small_models: int = 3
    max_large_models: int = 1
    browsing: str = "disabled"

    def target_seconds(self) -> float:
        if self.duration_hours is not None:
            return self.duration_hours * 3600.0
        if self.duration_minutes is not None:
            return self.duration_minutes * 60.0
        return 0.0


def parse_args(argv: list[str]) -> PacedLoopConfig:
    cfg = PacedLoopConfig()
    i = 0
    while i < len(argv):
        a = argv[i]
        def nxt():
            nonlocal i
            i += 1
            return argv[i]
        if a == "--duration-hours":
            cfg.duration_hours = float(nxt())
        elif a == "--duration-minutes":
            cfg.duration_minutes = float(nxt())
        elif a == "--checkin-minutes":
            cfg.checkin_minutes = int(nxt())
        elif a == "--checkpoint-minutes":
            cfg.checkpoint_minutes = int(nxt())
        elif a == "--lmstudio-base-url":
            cfg.lmstudio_base_url = nxt()
        elif a == "--main-model":
            cfg.main_model = nxt()
        elif a == "--per-call-timeout-seconds":
            cfg.per_call_timeout_seconds = int(nxt())
        elif a == "--final-answer-retry":
            cfg.final_answer_retry = True
        elif a == "--no-final-answer-retry":
            cfg.final_answer_retry = False
        elif a == "--max-small-models":
            cfg.max_small_models = int(nxt())
        elif a == "--max-large-models":
            cfg.max_large_models = int(nxt())
        elif a == "--browsing":
            cfg.browsing = nxt()
        i += 1
    return cfg


def overnight_green_allowed(*, target_seconds: float, elapsed_seconds: float,
                            min_overnight_seconds: float = 4 * 3600.0,
                            operator_stop: bool = False, panic: bool = False) -> bool:
    """GREEN-as-overnight requires reaching the target AND a meaningful (>=4h)
    real wall-clock run, with no stop/panic. A compressed run is never GREEN."""
    if operator_stop or panic:
        return False
    if elapsed_seconds + 1e-6 < target_seconds:
        return False
    return elapsed_seconds >= min_overnight_seconds


def verdict_for_run(*, target_seconds: float, elapsed_seconds: float,
                    operator_stop: bool = False, panic: bool = False,
                    boundaries_held: bool = True) -> str:
    if not boundaries_held or panic:
        return "RED_OVERNIGHT_BOUNDED_FULL_SEND_FAILED" if not boundaries_held \
            else "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL"
    if overnight_green_allowed(target_seconds=target_seconds, elapsed_seconds=elapsed_seconds,
                               operator_stop=operator_stop, panic=panic):
        return "GREEN_OVERNIGHT_BOUNDED_FULL_SEND_SOAK"
    return "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL"


def due_checkins(elapsed_seconds: float, checkin_minutes: int) -> int:
    """Number of hourly (or N-minute) check-ins that should have fired by now,
    based on REAL elapsed wall-clock time."""
    if checkin_minutes <= 0:
        return 0
    return int(elapsed_seconds // (checkin_minutes * 60)) + 1  # includes hour_00


def config_snapshot(cfg: PacedLoopConfig) -> dict:
    return asdict(cfg)
