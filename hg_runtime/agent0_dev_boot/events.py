"""Dev boot event and receipt schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agent0_dev_boot.types import advisory_payload

EVENT_TYPES = (
    "Agent0WakeRequested",
    "Agent0WakeStarted",
    "Agent0StorageReady",
    "Agent0ProviderReady",
    "Agent0OrgansRequired",
    "OrganBootStarted",
    "OrganBootCompleted",
    "OrganBootFailed",
    "BusAttachmentCreated",
    "ModelProviderSelected",
    "ModelResponseStarted",
    "ModelResponseDelta",
    "ModelResponseCompleted",
    "ModelResponseFailed",
    "OrganHeartbeat",
    "LivenessQueryReceived",
    "LivenessResponseProduced",
    "PanicStopRequested",
    "RuntimeStopRequested",
    "RuntimeStopped",
    "RuntimeFinalDigest",
    "CapabilityManifestBuilt",
)


@dataclass(frozen=True)
class DevBootEvent:
    event_type: str
    run_id: str
    sequence: int
    timestamp: str
    request_id: str
    organ_id: str | None = None
    provider_id: str | None = None
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {self.event_type}")

    def to_payload(self) -> dict[str, Any]:
        body = advisory_payload(
            schema="agent0-dev-boot-event",
            event_type=self.event_type,
            run_id=self.run_id,
            sequence=self.sequence,
            timestamp=self.timestamp,
            request_id=self.request_id,
            organ_id=self.organ_id,
            provider_id=self.provider_id,
            payload=self.payload or {},
        )
        body["event_hash"] = compute_record_hash({k: v for k, v in body.items() if k != "event_hash"})
        return body


def validate_event_sequence(events: list[dict[str, Any]]) -> tuple[bool, str]:
    if not events:
        return False, "no events"
    seqs = [e.get("sequence") for e in events]
    if seqs != sorted(seqs):
        return False, "sequence not monotonic"
    if events[-1].get("event_type") != "RuntimeFinalDigest":
        return False, "missing RuntimeFinalDigest"
    for e in events:
        if e.get("permission_granted") or e.get("authority_created"):
            return False, "event grants authority"
    return True, "ok"


def adapt_non_streaming_tokens(*, provider_id: str, model_id: str, run_id: str, text: str, sequence_start: int, timestamp: str) -> list[DevBootEvent]:
    return [
        DevBootEvent("ModelResponseStarted", run_id, sequence_start, timestamp, run_id, provider_id=provider_id),
        DevBootEvent("ModelResponseDelta", run_id, sequence_start + 1, timestamp, run_id, provider_id=provider_id, payload={"delta": text}),
        DevBootEvent("ModelResponseCompleted", run_id, sequence_start + 2, timestamp, run_id, provider_id=provider_id, payload={"model_id": model_id}),
    ]


__all__ = ["EVENT_TYPES", "DevBootEvent", "adapt_non_streaming_tokens", "validate_event_sequence"]
