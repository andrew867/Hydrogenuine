"""Replay-safe expiry evaluation — uses recorded timestamps only (CT-11 TIM-U4)."""

from __future__ import annotations

from typing import Callable

from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window


def evaluate_recorded_expiry(
    *,
    expires_at: str | None,
    recorded_now: str,
) -> tuple[bool, str]:
    """Evaluate validity at the recorded decision time (never wall clock)."""
    return validate_approval_window(expires_at, recorded_now)


def replay_independent_of_wall_clock(
    *,
    expires_at: str,
    recorded_now: str,
    advance_seconds: float,
    clock_advance: Callable[[float], None],
) -> bool:
    """Recorded decision unchanged after advancing injectable wall clock."""
    before = evaluate_recorded_expiry(expires_at=expires_at, recorded_now=recorded_now)
    clock_advance(advance_seconds)
    after = evaluate_recorded_expiry(expires_at=expires_at, recorded_now=recorded_now)
    return before == after


def verify_recorded_stale_refusal(
    *,
    expires_at: str,
    recorded_now: str,
) -> tuple[bool, str]:
    ok, reason = evaluate_recorded_expiry(expires_at=expires_at, recorded_now=recorded_now)
    if ok:
        return False, "expected_stale_refusal"
    if reason != STALE_APPROVAL:
        return False, reason
    return True, STALE_APPROVAL


__all__ = [
    "evaluate_recorded_expiry",
    "replay_independent_of_wall_clock",
    "verify_recorded_stale_refusal",
]
