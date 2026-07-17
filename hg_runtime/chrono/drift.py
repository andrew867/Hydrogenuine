"""CHRONO drift and ordering anomaly detection.

Drift is surfaced, never hidden. System/NTP disagreement and impossible
backward receipt ordering both degrade confidence and emit a finding.
"""

from __future__ import annotations

from datetime import datetime

from hg_runtime.chrono.schema import (
    DRIFT_EXTREME_S,
    DRIFT_TOLERANCE_S,
    ClockDriftFinding,
    DriftAction,
    DriftKind,
    TimeSyncResult,
)


def _parse(utc: str) -> datetime:
    return datetime.fromisoformat(utc)


def detect_drift(system: TimeSyncResult, ntp: TimeSyncResult) -> ClockDriftFinding | None:
    """Compare a system reading against an NTP reading.

    Returns a finding when |drift| exceeds tolerance, else None.
    """
    drift_seconds = (_parse(system.utc) - _parse(ntp.utc)).total_seconds()
    if abs(drift_seconds) <= DRIFT_TOLERANCE_S:
        return None
    severity = "high" if abs(drift_seconds) >= DRIFT_EXTREME_S else "medium"
    action = DriftAction.RESYNC if severity == "high" else DriftAction.DEGRADE_CONFIDENCE
    return ClockDriftFinding(
        kind=DriftKind.DRIFT_EXCEEDED,
        observed=system.utc,
        reference=ntp.utc,
        severity=severity,
        recommended_action=action,
        drift_seconds=drift_seconds,
        detail=f"system clock differs from {ntp.ntp_host or 'NTP'} by {drift_seconds:.3f}s",
    )


def detect_backward_ordering(previous: TimeSyncResult, current: TimeSyncResult) -> ClockDriftFinding | None:
    """Flag an impossible ordering: wall time went backward while monotonic advanced.

    Monotonic time is the tie-breaker. A wall-clock that precedes a prior receipt
    without a monotonic decrease is an impossible ordering.
    """
    wall_delta = (_parse(current.utc) - _parse(previous.utc)).total_seconds()
    monotonic_advanced = current.monotonic_seconds >= previous.monotonic_seconds
    if wall_delta < 0 and monotonic_advanced:
        return ClockDriftFinding(
            kind=DriftKind.BACKWARD_ORDERING,
            observed=current.utc,
            reference=previous.utc,
            severity="high",
            recommended_action=DriftAction.OPERATOR_REVIEW,
            drift_seconds=wall_delta,
            detail="wall clock moved backward while monotonic time advanced",
        )
    return None


__all__ = ["detect_backward_ordering", "detect_drift"]
