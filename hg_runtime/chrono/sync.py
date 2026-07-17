"""CHRONO sync orchestration.

Try the trusted source (NTP when allowed), fall back to system at reduced
confidence, and — when no source is usable — return UNKNOWN confidence rather
than ever inventing a date.
"""

from __future__ import annotations

from dataclasses import dataclass

from hg_runtime.chrono.drift import detect_drift
from hg_runtime.chrono.receipts import ChronoReceipt, create_receipt
from hg_runtime.chrono.schema import (
    ClockDriftFinding,
    TimeConfidence,
    TimeSourceKind,
    TimeSourceUnavailable,
    TimeSyncResult,
)
from hg_runtime.chrono.sources import FixtureTimeSource, NtpTimeSource, SystemTimeSource


@dataclass
class ChronoConfig:
    ntp_host: str = "pool.ntp.org"
    ntp_timeout_seconds: float = 3.0
    allow_network: bool = True
    write_local_state: bool = True
    offline_fixture: bool = False


@dataclass
class SyncOutcome:
    result: TimeSyncResult
    receipt: ChronoReceipt
    drift_finding: ClockDriftFinding | None = None


def sync_time(config: ChronoConfig | None = None) -> SyncOutcome:
    """Resolve current time with honest confidence grading.

    Order: fixture (if requested) -> NTP (if allowed) with system cross-check
    for drift -> system fallback (LOW) -> UNKNOWN (never invents a date).
    """
    config = config or ChronoConfig()

    if config.offline_fixture:
        result = FixtureTimeSource().read()
        return SyncOutcome(result=result, receipt=create_receipt(result))

    drift_finding: ClockDriftFinding | None = None

    if config.allow_network:
        try:
            ntp_result = NtpTimeSource(config.ntp_host, config.ntp_timeout_seconds).read()
        except TimeSourceUnavailable:
            ntp_result = None
        if ntp_result is not None:
            # Cross-check against the system clock to surface drift.
            try:
                system_result = SystemTimeSource().read()
                drift_finding = detect_drift(system_result, ntp_result)
                if drift_finding is not None:
                    ntp_result.drift_seconds = drift_finding.drift_seconds
            except Exception:
                pass
            receipt = create_receipt(ntp_result)
            if drift_finding is not None:
                receipt = create_receipt(ntp_result, drift_finding_ref=receipt.receipt_id)
            return SyncOutcome(result=ntp_result, receipt=receipt, drift_finding=drift_finding)

    # Fallback: system clock at reduced confidence.
    try:
        system_result = SystemTimeSource().read()
        return SyncOutcome(result=system_result, receipt=create_receipt(system_result))
    except Exception:
        pass

    # Nothing usable: UNKNOWN. Never invent a date.
    unknown = TimeSyncResult(
        utc="",
        monotonic_seconds=0.0,
        source=TimeSourceKind.SYSTEM,
        confidence=TimeConfidence.UNKNOWN,
        time_uncertain=True,
    )
    return SyncOutcome(result=unknown, receipt=create_receipt(unknown))


__all__ = ["ChronoConfig", "SyncOutcome", "sync_time"]
