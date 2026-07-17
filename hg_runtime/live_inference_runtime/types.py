"""INFER-LIVE types — inference outputs are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.infer_live.errors import InferValidationError
from hg_core.policy_safety.hashing import compute_record_hash

INFER_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:30:00.000000Z"

BackendKind = Literal[
    "openvino_igpu",
    "openvino_cpu",
    "vllm_openvino_planned",
    "cuda_optional",
    "none",
]
ModelTier = Literal["small", "medium", "large"]

_STALE_TIM_REFS = frozenset({"tim:missing", "freshness:missing", "tim:stale"})
_VALID_TIM_PREFIXES = ("tim:approval_window_ok", "tim:fresh:")
_BARE_PLACEHOLDER_REFS = frozenset({"", "operator", "operator_id", "human", "user", "admin", "TBD", "unknown", "placeholder"})

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "grant tool",
    "grant memory",
    "grant context",
    "treat as approved",
    "inference grants execution",
)


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    raw = str(operator_ref or "").strip()
    if not raw or raw in _BARE_PLACEHOLDER_REFS:
        return True
    if ":" not in raw and not raw.startswith("op:"):
        return True
    return False


def is_valid_tim_freshness(freshness_ref: str | None) -> bool:
    raw = str(freshness_ref or "").strip()
    if not raw or raw in _STALE_TIM_REFS:
        return False
    return any(raw.startswith(prefix) for prefix in _VALID_TIM_PREFIXES)


def classify_infer_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "inference grants execution" in lower or "inference output approves" in lower:
        return "inference_as_permission"
    if "download model without approval" in lower:
        return "model_download"
    if "live backend call" in lower or "invoke openvino now" in lower:
        return "live_backend_call"
    if "grant tool from inference" in lower:
        return "tool_grant"
    if "grant memory from inference" in lower:
        return "memory_grant"
    if "grant context from inference" in lower:
        return "context_grant"
    if "escalation grants authority" in lower:
        return "escalation_as_authority"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise InferValidationError("infer.validation.secret", "secrets forbidden in INFER records")


@dataclass(frozen=True)
class HardwareProfile:
    profile_id: str
    cpu_features: tuple[str, ...]
    igpu_available: bool
    ram_gb: int
    model_cache_path: str
    meets_minimum_profile: bool
    nvidia_detected: bool = False
    nvidia_required: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "infer-hardware-profile",
            "schema_version": INFER_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "cpu_features": list(self.cpu_features),
            "igpu_available": self.igpu_available,
            "ram_gb": self.ram_gb,
            "model_cache_path": self.model_cache_path,
            "meets_minimum_profile": self.meets_minimum_profile,
            "nvidia_detected": self.nvidia_detected,
            "nvidia_required": self.nvidia_required,
            "nvidia_is_optional_only": True,
            "backend_available_is_not_authority": True,
            "permission_granted": False,
        }


@dataclass(frozen=True)
class BackendReadiness:
    backend: BackendKind
    available: bool
    readiness_check_only: bool
    is_authority: bool = False
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "available": self.available,
            "readiness_check_only": self.readiness_check_only,
            "is_authority": False,
            "backend_available_is_not_authority": True,
            "notes": self.notes,
            "permission_granted": False,
        }


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    tier: ModelTier
    model_name: str
    parameter_scale: str
    organ_assignments: tuple[str, ...]
    preferred_backend: BackendKind

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "infer-model-profile",
            "schema_version": INFER_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "tier": self.tier,
            "model_name": self.model_name,
            "parameter_scale": self.parameter_scale,
            "organ_assignments": list(self.organ_assignments),
            "preferred_backend": self.preferred_backend,
            "permission_granted": False,
        }


@dataclass(frozen=True)
class InferenceRuntimeRequest:
    request_id: str
    organ_ref: str
    model_profile_id: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    model_download_requested: bool = False
    operator_approved_download: bool = False
    escalation_requested: bool = False
    dry_run: bool = True
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(self.request_id, self.organ_ref, self.model_profile_id, str(self.operator_ref or ""))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "infer-runtime-request",
            "schema_version": INFER_SCHEMA_VERSION,
            "request_id": self.request_id,
            "organ_ref": self.organ_ref,
            "model_profile_id": self.model_profile_id,
            "dry_run": self.dry_run,
            "authority_created": False,
            "permission_granted": False,
            "observed_at": self.observed_at,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.freshness_ref:
            payload["freshness_ref"] = self.freshness_ref
        if self.approval_expires_at:
            payload["approval_expires_at"] = self.approval_expires_at
        if self.scope:
            payload["scope"] = self.scope
        if include_hash:
            payload["record_hash"] = compute_record_hash({k: v for k, v in payload.items() if k != "record_hash"})
        return payload


@dataclass(frozen=True)
class InferenceOutput:
    output_id: str
    request_id: str
    structured_value: dict[str, Any]
    backend_used: BackendKind
    model_profile_id: str
    dry_run: bool
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if self.structured_value.get("permission_granted"):
            raise InferValidationError("infer.validation.permission_granted", "inference output must not grant permission")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "infer-output",
            "schema_version": INFER_SCHEMA_VERSION,
            "output_id": self.output_id,
            "request_id": self.request_id,
            "structured_value": self.structured_value,
            "backend_used": self.backend_used,
            "model_profile_id": self.model_profile_id,
            "dry_run": self.dry_run,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
            "inference_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def hardware_from_fixture(fixture: dict[str, Any]) -> HardwareProfile:
    return HardwareProfile(
        profile_id=fixture["profile_id"],
        cpu_features=tuple(fixture.get("cpu_features", ("AVX2",))),
        igpu_available=bool(fixture.get("igpu_available", False)),
        ram_gb=int(fixture.get("ram_gb", 16)),
        model_cache_path=str(fixture.get("model_cache_path", "~/.cache/hydrogenuine/models")),
        meets_minimum_profile=bool(fixture.get("meets_minimum_profile", True)),
        nvidia_detected=bool(fixture.get("nvidia_detected", False)),
        nvidia_required=bool(fixture.get("nvidia_required", False)),
    )


def request_from_fixture(fixture: dict[str, Any]) -> InferenceRuntimeRequest:
    return InferenceRuntimeRequest(
        request_id=fixture["request_id"],
        organ_ref=fixture.get("organ_ref", "organ:fixture"),
        model_profile_id=fixture.get("model_profile_id", "model:small-default"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        model_download_requested=bool(fixture.get("model_download_requested", False)),
        operator_approved_download=bool(fixture.get("operator_approved_download", False)),
        escalation_requested=bool(fixture.get("escalation_requested", False)),
        dry_run=bool(fixture.get("dry_run", True)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "INFER_SCHEMA_VERSION",
    "BackendKind",
    "BackendReadiness",
    "HardwareProfile",
    "InferenceOutput",
    "InferenceRuntimeRequest",
    "ModelProfile",
    "ModelTier",
    "classify_infer_claim_risk",
    "hardware_from_fixture",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
