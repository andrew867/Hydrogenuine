"""OpenVINO Watchtower schema — semantic telemetry types (advisory only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

WATCHTOWER_SCHEMA_VERSION = "1.0"

EventType = Literal[
    "WATCHTOWER_STARTED",
    "WATCHTOWER_STOPPED",
    "OPENVINO_RUNTIME_DETECTED",
    "OPENVINO_RUNTIME_MISSING",
    "MODEL_LOAD_STARTED",
    "MODEL_LOAD_COMPLETED",
    "MODEL_LOAD_FAILED",
    "MODEL_COMPILE_STARTED",
    "MODEL_COMPILE_COMPLETED",
    "MODEL_COMPILE_FAILED",
    "INFERENCE_REQUEST_RECEIVED",
    "INFERENCE_STARTED",
    "INFERENCE_CHUNK_EMITTED",
    "INFERENCE_COMPLETED",
    "INFERENCE_FAILED",
    "ORGAN_ACTIVITY_STARTED",
    "ORGAN_ACTIVITY_UPDATED",
    "ORGAN_ACTIVITY_COMPLETED",
    "QUEUE_DEPTH_CHANGED",
    "PROVIDER_HEALTH_CHANGED",
    "DEVICE_METRIC_UPDATED",
    "GPU_METRIC_UPDATED",
    "TELEMETRY_STALE",
    "TELEMETRY_CONTACT_LOST",
    "REDACTION_APPLIED",
]

ProviderMode = Literal["live-local", "fixture", "dry-run", "unavailable"]
FreshnessVerdict = Literal["fresh", "warning", "stale", "contact_lost"]
OrganState = Literal["idle", "active", "waiting", "blocked", "error", "stale"]


class TelemetryVerdict(str, Enum):
    FRESH = "fresh"
    WARNING = "warning"
    STALE = "stale"
    CONTACT_LOST = "contact_lost"


@dataclass
class TelemetryRedactionPolicy:
    raw_prompts_enabled: bool = False
    raw_completions_enabled: bool = False
    hidden_chain_of_thought_enabled: bool = False
    dev_preview_chars: int = 0
    show_hashes: bool = True
    show_lengths: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderStatus:
    provider_id: str | None = None
    mode: ProviderMode = "unavailable"
    reachable: bool = False
    healthy: bool = False
    openvino_present: bool = False
    runtime_version: str | None = None
    verdict: str = "YELLOW_PROVIDER_UNREACHABLE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelStatus:
    model_id: str | None = None
    model_path: str | None = None
    model_hash: str | None = None
    loaded: bool = False
    compile_duration_ms: float | None = None
    load_duration_ms: float | None = None
    last_load_at: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeviceStatus:
    device: str | None = None
    resolved_device: str | None = None
    compile_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeMetric:
    name: str
    value: float
    unit: str = ""
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InferenceSpan:
    span_id: str
    request_id: str
    organ_id: str | None = None
    task: str | None = None
    action_id: str | None = None
    model_id: str | None = None
    device: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float | None = None
    chunk_count: int = 0
    token_count: int = 0
    tokens_per_second: float | None = None
    queue_item_ref: str | None = None
    authority_chain_ref: str | None = None
    receipt_ref: str | None = None
    proof_ref: str | None = None
    status: Literal["active", "completed", "failed"] = "active"
    error: str | None = None
    prompt_hash: str | None = None
    prompt_length: int | None = None
    output_hash: str | None = None
    output_length: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganActivityEvent:
    organ_id: str
    state: OrganState = "idle"
    task: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InferenceEvent:
    event_type: EventType
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = field(default_factory=lambda: uuid4().hex)
    span_id: str | None = None
    request_id: str | None = None
    organ_id: str | None = None
    model_id: str | None = None
    device: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "openvino-watchtower-event",
            "schema_version": WATCHTOWER_SCHEMA_VERSION,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts": self.ts,
            "span_id": self.span_id,
            "request_id": self.request_id,
            "organ_id": self.organ_id,
            "model_id": self.model_id,
            "device": self.device,
            "payload": self.payload,
            "authority_created": False,
            "permission_granted": False,
            "advisory_only": True,
        }


@dataclass
class TelemetryFreshness:
    generated_at: str
    freshness_age_ms: float
    freshness_verdict: FreshnessVerdict
    warning_threshold_ms: float = 30_000.0
    stale_threshold_ms: float = 120_000.0
    contact_lost_threshold_ms: float = 300_000.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TelemetrySnapshot:
    generated_at: str
    snapshot_id: str
    freshness_age_ms: float
    freshness_verdict: FreshnessVerdict
    provider_status: ProviderStatus
    openvino_status: dict[str, Any]
    model_status: ModelStatus
    device_status: DeviceStatus
    active_inference_spans: list[InferenceSpan]
    recent_inference_spans: list[InferenceSpan]
    organ_activity: dict[str, OrganActivityEvent]
    queue_depths: dict[str, int]
    gpu_metrics: dict[str, float]
    process_metrics: dict[str, float]
    error_summary: dict[str, Any]
    receipt_refs: list[str]
    proof_refs: list[str]
    redaction: TelemetryRedactionPolicy = field(default_factory=TelemetryRedactionPolicy)
    authority_created: bool = False
    permission_granted: bool = False
    advisory_only: bool = True
    request_count: int = 0
    error_count: int = 0
    rolling_latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "openvino-watchtower-snapshot",
            "schema_version": WATCHTOWER_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "snapshot_id": self.snapshot_id,
            "freshness_age_ms": self.freshness_age_ms,
            "freshness_verdict": self.freshness_verdict,
            "provider_status": self.provider_status.to_dict(),
            "openvino_status": self.openvino_status,
            "model_status": self.model_status.to_dict(),
            "device_status": self.device_status.to_dict(),
            "active_inference_spans": [s.to_dict() for s in self.active_inference_spans],
            "recent_inference_spans": [s.to_dict() for s in self.recent_inference_spans],
            "organ_activity": {k: v.to_dict() for k, v in self.organ_activity.items()},
            "queue_depths": dict(self.queue_depths),
            "gpu_metrics": dict(self.gpu_metrics),
            "process_metrics": dict(self.process_metrics),
            "error_summary": dict(self.error_summary),
            "receipt_refs": list(self.receipt_refs),
            "proof_refs": list(self.proof_refs),
            "redaction": self.redaction.to_dict(),
            "authority_created": False,
            "permission_granted": False,
            "advisory_only": True,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "rolling_latency_ms": self.rolling_latency_ms,
        }


def new_span_id() -> str:
    return f"span-{uuid4().hex[:12]}"


def new_snapshot_id() -> str:
    return f"snap-{uuid4().hex[:12]}"


def validate_event_dict(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("event_type", "ts", "event_id"):
        if key not in data:
            errors.append(f"missing:{key}")
    if data.get("authority_created"):
        errors.append("authority_created_must_be_false")
    if data.get("permission_granted"):
        errors.append("permission_granted_must_be_false")
    return errors


def validate_snapshot_dict(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "generated_at",
        "snapshot_id",
        "freshness_age_ms",
        "freshness_verdict",
        "provider_status",
        "openvino_status",
        "model_status",
        "device_status",
    ):
        if key not in data:
            errors.append(f"missing:{key}")
    if data.get("authority_created"):
        errors.append("authority_created_must_be_false")
    if data.get("permission_granted"):
        errors.append("permission_granted_must_be_false")
    verdict = str(data.get("freshness_verdict", ""))
    provider = data.get("provider_status") or {}
    if verdict == "fresh" and not provider.get("healthy") and provider.get("mode") == "unavailable":
        errors.append("fake_green_unavailable_provider")
    return errors


__all__ = [
    "DeviceStatus",
    "EventType",
    "FreshnessVerdict",
    "InferenceEvent",
    "InferenceSpan",
    "ModelStatus",
    "OrganActivityEvent",
    "OrganState",
    "ProviderMode",
    "ProviderStatus",
    "RuntimeMetric",
    "TelemetryFreshness",
    "TelemetryRedactionPolicy",
    "TelemetrySnapshot",
    "TelemetryVerdict",
    "WATCHTOWER_SCHEMA_VERSION",
    "new_snapshot_id",
    "new_span_id",
    "validate_event_dict",
    "validate_snapshot_dict",
]
