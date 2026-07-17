"""CHRONO schema types — time is evidence, not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.chrono.hash import chrono_hash

CHRONO_SCHEMA_VERSION = "chrono/1"

# Deterministic fixture instant (matches the WILL module fixture clock).
FIXTURE_UTC = "2026-06-15T04:00:00+00:00"
FIXTURE_MONOTONIC = 1000.0


class TimeSourceKind(str, Enum):
    NTP = "NTP"
    SYSTEM = "SYSTEM"
    FIXTURE = "FIXTURE"


class TimeConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class DriftKind(str, Enum):
    DRIFT_EXCEEDED = "DRIFT_EXCEEDED"
    BACKWARD_ORDERING = "BACKWARD_ORDERING"
    SOURCE_DISAGREEMENT = "SOURCE_DISAGREEMENT"


class DriftAction(str, Enum):
    RECORD = "RECORD"
    DEGRADE_CONFIDENCE = "DEGRADE_CONFIDENCE"
    RESYNC = "RESYNC"
    OPERATOR_REVIEW = "OPERATOR_REVIEW"


# Confidence grading thresholds (seconds).
NTP_HIGH_ROUNDTRIP_S = 0.25
NTP_MEDIUM_ROUNDTRIP_S = 2.0
# Drift tolerance: system vs NTP delta beyond this emits a finding.
DRIFT_TOLERANCE_S = 2.0
# Beyond this, the clock is treated as clearly wrong.
DRIFT_EXTREME_S = 300.0


class TimeSource:
    """Abstract time-source contract.

    A source returns a TimeSyncResult or raises TimeSourceUnavailable.
    Sources never grant authority and never fabricate a timestamp.
    """

    kind: TimeSourceKind

    def read(self) -> "TimeSyncResult":  # pragma: no cover - interface
        # Fail closed: the abstract contract cannot produce a real reading and
        # never fabricates one. Concrete sources must override read().
        raise TimeSourceUnavailable(
            source=str(getattr(self, "kind", "abstract")),
            detail="TimeSource.read is an interface; concrete source must implement it",
        )


class TimeSourceUnavailable(Exception):
    """Raised when a source cannot produce a real reading."""

    def __init__(self, source: str, detail: str) -> None:
        super().__init__(detail)
        self.source = source
        self.detail = detail


@dataclass
class TimeSyncResult:
    utc: str
    monotonic_seconds: float
    source: TimeSourceKind
    confidence: TimeConfidence
    time_uncertain: bool = False
    ntp_host: str | None = None
    drift_seconds: float | None = None
    roundtrip_seconds: float | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "chrono-sync-result",
            "utc": self.utc,
            "monotonic_seconds": self.monotonic_seconds,
            "source": self.source.value,
            "confidence": self.confidence.value,
            "time_uncertain": self.time_uncertain,
            "ntp_host": self.ntp_host,
            "drift_seconds": self.drift_seconds,
            "roundtrip_seconds": self.roundtrip_seconds,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class ClockDriftFinding:
    kind: DriftKind
    observed: str
    reference: str
    severity: str
    recommended_action: DriftAction
    drift_seconds: float | None = None
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "chrono-drift-finding",
            "kind": self.kind.value,
            "observed": self.observed,
            "reference": self.reference,
            "severity": self.severity,
            "recommended_action": self.recommended_action.value,
            "drift_seconds": self.drift_seconds,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class Agent0TimeContext:
    utc_now: str
    monotonic_seconds: float
    source: TimeSourceKind
    time_confidence: TimeConfidence
    time_uncertain: bool
    receipt_ref: str
    local_time_optional: str | None = None
    ntp_host: str | None = None
    drift_seconds: float | None = None
    drift_finding_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "chrono-agent0-time-context",
            "version": CHRONO_SCHEMA_VERSION,
            "utc_now": self.utc_now,
            "local_time_optional": self.local_time_optional,
            "monotonic_seconds": self.monotonic_seconds,
            "source": self.source.value,
            "ntp_host": self.ntp_host,
            "drift_seconds": self.drift_seconds,
            "drift_finding_ref": self.drift_finding_ref,
            "time_confidence": self.time_confidence.value,
            "time_uncertain": self.time_uncertain,
            "receipt_ref": self.receipt_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["content_hash"] = chrono_hash(payload)
        return payload


__all__ = [
    "CHRONO_SCHEMA_VERSION",
    "DRIFT_EXTREME_S",
    "DRIFT_TOLERANCE_S",
    "FIXTURE_MONOTONIC",
    "FIXTURE_UTC",
    "NTP_HIGH_ROUNDTRIP_S",
    "NTP_MEDIUM_ROUNDTRIP_S",
    "Agent0TimeContext",
    "ClockDriftFinding",
    "DriftAction",
    "DriftKind",
    "TimeConfidence",
    "TimeSource",
    "TimeSourceKind",
    "TimeSourceUnavailable",
    "TimeSyncResult",
]
