"""Boot epoch types — named interval beginning at Agent Zero startup."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.chrono.hash import chrono_hash
from hg_runtime.chrono.schema import TimeConfidence, TimeSourceKind


class EpochConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class QuorumStatus(str, Enum):
    QUORUM = "QUORUM"
    PARTIAL = "PARTIAL"
    SYSTEM_ONLY = "SYSTEM_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class TimeSourceSample:
    source: TimeSourceKind
    utc: str
    monotonic_seconds: float
    roundtrip_seconds: float | None = None
    ntp_host: str | None = None
    offset_seconds: float | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "utc": self.utc,
            "monotonic_seconds": self.monotonic_seconds,
            "roundtrip_seconds": self.roundtrip_seconds,
            "ntp_host": self.ntp_host,
            "offset_seconds": self.offset_seconds,
        }


@dataclass
class TimeSourceQuorum:
    status: QuorumStatus
    samples: list[TimeSourceSample] = field(default_factory=list)
    ntp_reachable: bool = False
    system_available: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "ntp_reachable": self.ntp_reachable,
            "system_available": self.system_available,
            "sample_count": len(self.samples),
            "samples": [s.to_payload() for s in self.samples],
        }


@dataclass
class ClockDriftWindow:
    drift_seconds: float | None
    window_seconds: float
    uncertain: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "drift_seconds": self.drift_seconds,
            "window_seconds": self.window_seconds,
            "uncertain": self.uncertain,
        }


@dataclass
class MonotonicOrigin:
    origin_ns: int
    origin_seconds: float

    def to_payload(self) -> dict[str, Any]:
        return {"origin_ns": self.origin_ns, "origin_seconds": self.origin_seconds}


@dataclass
class ExternalWitnessRef:
    backend: str
    commit_sha: str | None = None
    verified: bool = False
    boot_bundle_sha256: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "commit_sha": self.commit_sha,
            "verified": self.verified,
            "boot_bundle_sha256": self.boot_bundle_sha256,
        }


@dataclass
class EpochReceiptRef:
    receipt_id: str
    epoch_id: str
    epoch_lock_id: str
    receipt_sequence: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "epoch_id": self.epoch_id,
            "epoch_lock_id": self.epoch_lock_id,
            "receipt_sequence": self.receipt_sequence,
        }


@dataclass
class BootEpoch:
    epoch_id: str
    agent_code_id: str
    started_utc: str
    monotonic_origin: MonotonicOrigin
    quorum: TimeSourceQuorum
    drift_window: ClockDriftWindow
    repo_head: str = ""
    boot_bundle_sha256: str | None = None
    external_witness: ExternalWitnessRef | None = None

    @classmethod
    def new_id(cls, agent_code_id: str = "agent0") -> str:
        return f"epoch-{agent_code_id}-{uuid.uuid4().hex[:12]}"

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "chrono-boot-epoch",
            "epoch_id": self.epoch_id,
            "agent_code_id": self.agent_code_id,
            "started_utc": self.started_utc,
            "monotonic_origin": self.monotonic_origin.to_payload(),
            "quorum": self.quorum.to_payload(),
            "drift_window": self.drift_window.to_payload(),
            "repo_head": self.repo_head,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "external_witness": self.external_witness.to_payload() if self.external_witness else None,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def monotonic_origin_now() -> MonotonicOrigin:
    ns = time.monotonic_ns()
    return MonotonicOrigin(origin_ns=ns, origin_seconds=ns / 1_000_000_000)


def compute_epoch_lock_id(material: dict[str, Any]) -> str:
    return chrono_hash(material).removeprefix("sha256:")


__all__ = [
    "BootEpoch",
    "ClockDriftWindow",
    "EpochConfidence",
    "EpochReceiptRef",
    "ExternalWitnessRef",
    "MonotonicOrigin",
    "QuorumStatus",
    "TimeSourceQuorum",
    "TimeSourceSample",
    "compute_epoch_lock_id",
    "monotonic_origin_now",
]
