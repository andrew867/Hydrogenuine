"""CHRONO drift and backward-ordering detection tests."""

from __future__ import annotations

from hg_runtime.chrono.drift import detect_backward_ordering, detect_drift
from hg_runtime.chrono.schema import DriftKind, TimeConfidence, TimeSourceKind, TimeSyncResult


def _r(utc: str, mono: float, source=TimeSourceKind.SYSTEM) -> TimeSyncResult:
    return TimeSyncResult(utc, mono, source, TimeConfidence.LOW)


def test_drift_within_tolerance_returns_none():
    ntp = _r("2026-06-15T04:00:00+00:00", 10.0, TimeSourceKind.NTP)
    system = _r("2026-06-15T04:00:01+00:00", 10.0)
    assert detect_drift(system, ntp) is None


def test_drift_exceeded_emits_finding():
    ntp = _r("2026-06-15T04:00:00+00:00", 10.0, TimeSourceKind.NTP)
    system = _r("2026-06-15T04:01:00+00:00", 10.0)
    finding = detect_drift(system, ntp)
    assert finding is not None
    assert finding.kind == DriftKind.DRIFT_EXCEEDED
    assert finding.drift_seconds == 60.0


def test_extreme_drift_recommends_resync():
    ntp = _r("2026-06-15T04:00:00+00:00", 10.0, TimeSourceKind.NTP)
    system = _r("2026-06-15T05:00:00+00:00", 10.0)
    finding = detect_drift(system, ntp)
    assert finding is not None
    assert finding.severity == "high"
    assert finding.recommended_action.value == "RESYNC"


def test_backward_ordering_detected():
    previous = _r("2026-06-15T04:00:00+00:00", 100.0)
    current = _r("2026-06-15T03:59:00+00:00", 101.0)
    finding = detect_backward_ordering(previous, current)
    assert finding is not None
    assert finding.kind == DriftKind.BACKWARD_ORDERING


def test_forward_ordering_ok():
    previous = _r("2026-06-15T04:00:00+00:00", 100.0)
    current = _r("2026-06-15T04:00:05+00:00", 105.0)
    assert detect_backward_ordering(previous, current) is None


def test_drift_finding_frozen_constants():
    ntp = _r("2026-06-15T04:00:00+00:00", 10.0, TimeSourceKind.NTP)
    system = _r("2026-06-15T04:01:00+00:00", 10.0)
    payload = detect_drift(system, ntp).to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
