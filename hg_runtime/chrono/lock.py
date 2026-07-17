"""CHRONO Lock — bounded confidence lock over time sources at boot."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.chrono.epoch import (
    BootEpoch,
    ClockDriftWindow,
    EpochConfidence,
    ExternalWitnessRef,
    MonotonicOrigin,
    QuorumStatus,
    TimeSourceQuorum,
    TimeSourceSample,
    compute_epoch_lock_id,
    monotonic_origin_now,
)
from hg_runtime.chrono.schema import DRIFT_TOLERANCE_S, TimeConfidence, TimeSourceKind
from hg_runtime.chrono.sync import ChronoConfig, SyncOutcome, sync_time

WORKSPACE = Path(__file__).resolve().parents[2]

NTP_HIGH_OFFSET_S = DRIFT_TOLERANCE_S

CHRONO_LOCK_BOOT_INSTRUCTION = (
    "You have a CHRONO lock for this boot epoch. "
    "It binds system time, NTP sample, monotonic origin, boot bundle hash, "
    "and optional external witness anchor. "
    "Treat this as continuity evidence, not authority. "
    "The lock does not grant permission."
)


@dataclass
class ChronoLock:
    epoch_id: str
    epoch_lock_id: str
    agent_code_id: str
    created_utc: str
    system_utc_at_lock: str
    ntp_utc_at_lock: str | None
    ntp_host: str | None
    ntp_offset_seconds: float | None
    ntp_roundtrip_seconds: float | None
    monotonic_origin_ns: int
    source_samples: list[dict[str, Any]] = field(default_factory=list)
    source_quorum_status: str = QuorumStatus.UNAVAILABLE.value
    drift_window_seconds: float = 0.0
    time_confidence: EpochConfidence = EpochConfidence.UNKNOWN
    time_uncertain: bool = True
    repo_head: str = ""
    boot_bundle_sha256: str | None = None
    external_anchor_commit_sha: str | None = None
    external_anchor_verified: bool = False
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "chrono-lock",
            "epoch_id": self.epoch_id,
            "epoch_lock_id": self.epoch_lock_id,
            "agent_code_id": self.agent_code_id,
            "created_utc": self.created_utc,
            "system_utc_at_lock": self.system_utc_at_lock,
            "ntp_utc_at_lock": self.ntp_utc_at_lock,
            "ntp_host": self.ntp_host,
            "ntp_offset_seconds": self.ntp_offset_seconds,
            "ntp_roundtrip_seconds": self.ntp_roundtrip_seconds,
            "monotonic_origin_ns": self.monotonic_origin_ns,
            "source_samples": self.source_samples,
            "source_quorum_status": self.source_quorum_status,
            "drift_window_seconds": self.drift_window_seconds,
            "time_confidence": self.time_confidence.value,
            "time_uncertain": self.time_uncertain,
            "repo_head": self.repo_head,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "external_anchor_commit_sha": self.external_anchor_commit_sha,
            "external_anchor_verified": self.external_anchor_verified,
            "advisory_only": self.advisory_only,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
        }
        payload["content_hash"] = compute_epoch_lock_id(_lock_material(payload))
        return payload


def _lock_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        k: payload[k]
        for k in (
            "epoch_id",
            "agent_code_id",
            "created_utc",
            "system_utc_at_lock",
            "ntp_utc_at_lock",
            "ntp_host",
            "ntp_offset_seconds",
            "ntp_roundtrip_seconds",
            "monotonic_origin_ns",
            "source_samples",
            "source_quorum_status",
            "drift_window_seconds",
            "repo_head",
            "boot_bundle_sha256",
            "external_anchor_commit_sha",
            "external_anchor_verified",
        )
        if k in payload
    }


def _git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _samples_from_outcome(outcome: SyncOutcome) -> tuple[list[TimeSourceSample], TimeSourceQuorum]:
    result = outcome.result
    samples = [
        TimeSourceSample(
            source=result.source,
            utc=result.utc,
            monotonic_seconds=result.monotonic_seconds,
            roundtrip_seconds=result.roundtrip_seconds,
            ntp_host=result.ntp_host,
            offset_seconds=result.drift_seconds,
        )
    ]
    ntp_ok = result.source == TimeSourceKind.NTP
    system_ok = bool(result.utc)
    if ntp_ok:
        status = QuorumStatus.QUORUM
    elif system_ok and result.source == TimeSourceKind.SYSTEM:
        status = QuorumStatus.SYSTEM_ONLY
    elif system_ok:
        status = QuorumStatus.PARTIAL
    else:
        status = QuorumStatus.UNAVAILABLE
    quorum = TimeSourceQuorum(
        status=status,
        samples=samples,
        ntp_reachable=ntp_ok,
        system_available=system_ok,
    )
    return samples, quorum


def grade_epoch_confidence(
    *,
    ntp_reachable: bool,
    ntp_offset_seconds: float | None,
    monotonic_recorded: bool,
    external_anchor_verified: bool,
    system_only: bool,
    time_uncertain: bool,
    fixture_mode: bool = False,
) -> EpochConfidence:
    if not monotonic_recorded:
        return EpochConfidence.UNKNOWN
    offset_ok = ntp_offset_seconds is None or abs(ntp_offset_seconds) <= NTP_HIGH_OFFSET_S
    if fixture_mode and monotonic_recorded:
        return EpochConfidence.HIGH if external_anchor_verified else EpochConfidence.MEDIUM
    if ntp_reachable and offset_ok and monotonic_recorded and external_anchor_verified:
        return EpochConfidence.HIGH
    if ntp_reachable and offset_ok and monotonic_recorded:
        return EpochConfidence.MEDIUM
    if external_anchor_verified and monotonic_recorded and not ntp_reachable and not time_uncertain:
        return EpochConfidence.MEDIUM
    if system_only or time_uncertain:
        return EpochConfidence.LOW
    return EpochConfidence.UNKNOWN


@dataclass
class ChronoLockOutcome:
    lock: ChronoLock
    epoch: BootEpoch
    sync_outcome: SyncOutcome
    receipt_sequence: int = 0


def create_chrono_lock(
    *,
    agent_code_id: str = "agent0",
    config: ChronoConfig | None = None,
    workspace: Path | None = None,
    boot_bundle_sha256: str | None = None,
    external_anchor_commit_sha: str | None = None,
    external_anchor_verified: bool = False,
) -> ChronoLockOutcome:
    """Create a BootEpoch and ChronoLock before Agent Zero boot context is built."""
    ws = workspace or WORKSPACE
    config = config or ChronoConfig()
    sync_outcome = sync_time(config)
    result = sync_outcome.result
    samples, quorum = _samples_from_outcome(sync_outcome)
    origin = monotonic_origin_now()
    now = datetime.now(timezone.utc).isoformat()
    epoch_id = BootEpoch.new_id(agent_code_id)
    repo_head = _git_head(ws)

    drift_window = ClockDriftWindow(
        drift_seconds=result.drift_seconds,
        window_seconds=abs(result.drift_seconds) if result.drift_seconds is not None else 0.0,
        uncertain=result.time_uncertain,
    )

    witness = None
    if external_anchor_commit_sha or boot_bundle_sha256:
        witness = ExternalWitnessRef(
            backend="github",
            commit_sha=external_anchor_commit_sha,
            verified=external_anchor_verified,
            boot_bundle_sha256=boot_bundle_sha256,
        )

    epoch = BootEpoch(
        epoch_id=epoch_id,
        agent_code_id=agent_code_id,
        started_utc=now,
        monotonic_origin=origin,
        quorum=quorum,
        drift_window=drift_window,
        repo_head=repo_head,
        boot_bundle_sha256=boot_bundle_sha256,
        external_witness=witness,
    )

    system_utc = result.utc if result.source != TimeSourceKind.NTP else ""
    ntp_utc = result.utc if result.source == TimeSourceKind.NTP else None
    ntp_offset = result.drift_seconds if result.source == TimeSourceKind.NTP else None

    # If NTP, also capture system as secondary when drift finding exists.
    if result.source == TimeSourceKind.NTP and sync_outcome.drift_finding:
        ntp_offset = sync_outcome.drift_finding.drift_seconds

    confidence = grade_epoch_confidence(
        ntp_reachable=quorum.ntp_reachable,
        ntp_offset_seconds=ntp_offset,
        monotonic_recorded=True,
        external_anchor_verified=external_anchor_verified,
        system_only=quorum.status == QuorumStatus.SYSTEM_ONLY,
        time_uncertain=result.time_uncertain,
        fixture_mode=config.offline_fixture or result.source == TimeSourceKind.FIXTURE,
    )

    lock = ChronoLock(
        epoch_id=epoch_id,
        epoch_lock_id="",  # filled below
        agent_code_id=agent_code_id,
        created_utc=now,
        system_utc_at_lock=system_utc or result.utc,
        ntp_utc_at_lock=ntp_utc,
        ntp_host=result.ntp_host,
        ntp_offset_seconds=ntp_offset,
        ntp_roundtrip_seconds=result.roundtrip_seconds,
        monotonic_origin_ns=origin.origin_ns,
        source_samples=[s.to_payload() for s in samples],
        source_quorum_status=quorum.status.value,
        drift_window_seconds=drift_window.window_seconds,
        time_confidence=confidence,
        time_uncertain=result.time_uncertain or confidence in {EpochConfidence.LOW, EpochConfidence.UNKNOWN},
        repo_head=repo_head,
        boot_bundle_sha256=boot_bundle_sha256,
        external_anchor_commit_sha=external_anchor_commit_sha,
        external_anchor_verified=external_anchor_verified,
    )
    material = _lock_material(lock.to_payload())
    lock.epoch_lock_id = compute_epoch_lock_id(material)
    return ChronoLockOutcome(lock=lock, epoch=epoch, sync_outcome=sync_outcome)


def verify_epoch_lock_id(lock: ChronoLock) -> bool:
    material = _lock_material(lock.to_payload())
    return compute_epoch_lock_id(material) == lock.epoch_lock_id


__all__ = [
    "CHRONO_LOCK_BOOT_INSTRUCTION",
    "ChronoLock",
    "ChronoLockOutcome",
    "create_chrono_lock",
    "grade_epoch_confidence",
    "verify_epoch_lock_id",
]
