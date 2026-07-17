"""Live provider schemas — identity, health, output receipts."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.live_provider.errors import LiveProviderConfigError

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/live_provider_policy.json"


class ProviderRuntimeMode(str, Enum):
    LOCAL_DEV = "local_dev"
    DRY_AUTONOMY = "dry_autonomy"
    UNAVAILABLE = "unavailable"


class LiveProviderKind(str, Enum):
    LM_STUDIO = "lm_studio"
    LLAMA_CPP = "llama_cpp"
    OPENVINO = "openvino"
    VLLM = "vllm"
    HTTP_OPENAI_COMPATIBLE = "http_openai_compatible"
    DRY_UNAVAILABLE = "dry_unavailable"


class LiveProviderVerdict(str, Enum):
    GREEN_LIVE_PROVIDER_AVAILABLE = "GREEN_LIVE_PROVIDER_AVAILABLE"
    GREEN_LIVE_PROVIDER_OUTPUT_VALID = "GREEN_LIVE_PROVIDER_OUTPUT_VALID"
    YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED = "YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED"
    YELLOW_LOCAL_MODEL_NOT_CONFIGURED = "YELLOW_LOCAL_MODEL_NOT_CONFIGURED"
    YELLOW_LM_STUDIO_NOT_RUNNING = "YELLOW_LM_STUDIO_NOT_RUNNING"
    YELLOW_LLAMA_CPP_NOT_RUNNING = "YELLOW_LLAMA_CPP_NOT_RUNNING"
    YELLOW_OPENVINO_NOT_AVAILABLE = "YELLOW_OPENVINO_NOT_AVAILABLE"
    YELLOW_VLLM_NOT_AVAILABLE = "YELLOW_VLLM_NOT_AVAILABLE"
    YELLOW_PROVIDER_HEALTH_DEGRADED = "YELLOW_PROVIDER_HEALTH_DEGRADED"
    YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED = "YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED"
    YELLOW_PROVIDER_JSON_INVALID_DEFERRED = "YELLOW_PROVIDER_JSON_INVALID_DEFERRED"
    RED_PROVIDER_OUTPUT_WITHOUT_RECEIPT = "RED_PROVIDER_OUTPUT_WITHOUT_RECEIPT"
    RED_PROVIDER_IDENTITY_MISSING = "RED_PROVIDER_IDENTITY_MISSING"
    RED_MODEL_IDENTITY_MISSING = "RED_MODEL_IDENTITY_MISSING"
    RED_PROVIDER_UNAVAILABLE_TREATED_GREEN = "RED_PROVIDER_UNAVAILABLE_TREATED_GREEN"
    RED_EMPTY_PROVIDER_OUTPUT_TREATED_GREEN = "RED_EMPTY_PROVIDER_OUTPUT_TREATED_GREEN"
    RED_INVALID_JSON_TREATED_GREEN = "RED_INVALID_JSON_TREATED_GREEN"
    RED_FALLBACK_TEXT_TREATED_AS_COGNITION = "RED_FALLBACK_TEXT_TREATED_AS_COGNITION"
    RED_FIXTURE_TEXT_TREATED_AS_COGNITION = "RED_FIXTURE_TEXT_TREATED_AS_COGNITION"
    RED_MOCK_TEXT_TREATED_AS_COGNITION = "RED_MOCK_TEXT_TREATED_AS_COGNITION"
    RED_PROVIDER_RECEIPT_HASH_MISMATCH = "RED_PROVIDER_RECEIPT_HASH_MISMATCH"
    RED_PROVIDER_HEALTH_FAKE_GREEN = "RED_PROVIDER_HEALTH_FAKE_GREEN"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_live_provider_policy(*, path: Path | None = None) -> dict[str, Any]:
    policy_path = path or POLICY_PATH
    if not policy_path.is_file():
        return {}
    return json.loads(policy_path.read_text(encoding="utf-8"))


@dataclass
class ProviderIdentity:
    provider_id: str
    provider_kind: LiveProviderKind
    provider_name: str
    transport: str
    runtime_mode: ProviderRuntimeMode
    endpoint_ref: str | None = None
    configured_at: str = field(default_factory=now_iso)
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_kind": self.provider_kind.value,
            "provider_name": self.provider_name,
            "endpoint_ref": self.endpoint_ref,
            "transport": self.transport,
            "runtime_mode": self.runtime_mode.value,
            "configured_at": self.configured_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ProviderIdentity:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        digest = compute_record_hash(body)
        return ProviderIdentity(**{**self.__dict__, "hash": digest})


@dataclass
class ModelIdentity:
    model_id: str
    provider_ref: str
    model_name: str | None = None
    model_family: str | None = None
    quant_id: str | None = None
    context_length: int | None = None
    backend: str | None = None
    device: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "model_family": self.model_family,
            "quant_id": self.quant_id,
            "context_length": self.context_length,
            "backend": self.backend,
            "device": self.device,
            "provider_ref": self.provider_ref,
            "hash": self.hash,
        }

    def with_hash(self) -> ModelIdentity:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        digest = compute_record_hash(body)
        return ModelIdentity(**{**self.__dict__, "hash": digest})


@dataclass
class ProviderHealthReceipt:
    health_receipt_id: str
    provider_ref: str
    checked_at: str
    available: bool
    verdict: LiveProviderVerdict
    model_ref: str | None = None
    latency_ms: int | None = None
    context_length: int | None = None
    tokens_per_second_estimate: float | None = None
    failure_reason: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "health_receipt_id": self.health_receipt_id,
            "provider_ref": self.provider_ref,
            "model_ref": self.model_ref,
            "checked_at": self.checked_at,
            "available": self.available,
            "latency_ms": self.latency_ms,
            "context_length": self.context_length,
            "tokens_per_second_estimate": self.tokens_per_second_estimate,
            "failure_reason": self.failure_reason,
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> ProviderHealthReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        digest = compute_record_hash(body)
        return ProviderHealthReceipt(**{**self.__dict__, "hash": digest})


@dataclass
class ProviderOutputReceipt:
    provider_output_receipt_id: str
    request_ref: str
    provider_ref: str
    model_ref: str
    prompt_hash: str
    response_hash: str
    output_text_hash: str
    json_valid: bool
    latency_ms: int
    verdict: LiveProviderVerdict
    raw_response_ref: str | None = None
    schema_valid: bool | None = None
    token_counts: dict[str, int] | None = None
    finish_reason: str | None = None
    created_at: str = field(default_factory=now_iso)
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider_output_receipt_id": self.provider_output_receipt_id,
            "request_ref": self.request_ref,
            "provider_ref": self.provider_ref,
            "model_ref": self.model_ref,
            "prompt_hash": self.prompt_hash,
            "response_hash": self.response_hash,
            "raw_response_ref": self.raw_response_ref,
            "output_text_hash": self.output_text_hash,
            "json_valid": self.json_valid,
            "schema_valid": self.schema_valid,
            "latency_ms": self.latency_ms,
            "token_counts": self.token_counts,
            "finish_reason": self.finish_reason,
            "created_at": self.created_at,
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> ProviderOutputReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        digest = compute_record_hash(body)
        return ProviderOutputReceipt(**{**self.__dict__, "hash": digest})


@dataclass
class ProviderRouteDecision:
    route_id: str
    provider_ref: str
    model_ref: str | None
    provider_kind: LiveProviderKind
    verdict: LiveProviderVerdict
    reason: str
    created_at: str = field(default_factory=now_iso)
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "provider_ref": self.provider_ref,
            "model_ref": self.model_ref,
            "provider_kind": self.provider_kind.value,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ProviderRouteDecision:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        digest = compute_record_hash(body)
        return ProviderRouteDecision(**{**self.__dict__, "hash": digest})


@dataclass
class ProviderRequest:
    request_id: str
    prompt_hash: str
    role: str
    json_required: bool = True
    created_at: str = field(default_factory=now_iso)


@dataclass
class ProviderResponse:
    request_ref: str
    output_text: str
    output_receipt: ProviderOutputReceipt
    provider_identity: ProviderIdentity
    model_identity: ModelIdentity


@dataclass
class ProviderFailure:
    failure_id: str
    request_ref: str | None
    verdict: LiveProviderVerdict
    reason: str
    health_receipt_ref: str | None = None
    output_receipt_ref: str | None = None
    created_at: str = field(default_factory=now_iso)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def validate_policy_constraints(policy: dict[str, Any] | None = None) -> None:
    pol = policy or load_live_provider_policy()
    if pol.get("live_writes_allowed") is True:
        raise LiveProviderConfigError("RED_PHASE_15_LIVE_WRITES_NOT_ALLOWED")
    if pol.get("external_side_effects_allowed") is True:
        raise LiveProviderConfigError("RED_PHASE_15_EXTERNAL_SIDE_EFFECTS_NOT_ALLOWED")
    if pol.get("fallback_as_cognition_allowed") is True:
        raise LiveProviderConfigError("RED_FALLBACK_TEXT_TREATED_AS_COGNITION")
    if pol.get("fixture_as_cognition_allowed") is True:
        raise LiveProviderConfigError("RED_FIXTURE_TEXT_TREATED_AS_COGNITION")
    if pol.get("mock_as_cognition_allowed") is True:
        raise LiveProviderConfigError("RED_MOCK_TEXT_TREATED_AS_COGNITION")
