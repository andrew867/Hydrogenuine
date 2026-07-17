"""Model Provider Fabric types — advisory only, no authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

FABRIC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T23:30:00.000000Z"

ProviderType = Literal[
    "openvino_windows",
    "openvino_inprocess",
    "openai_compatible",
    "anthropic_compatible",
    "xai_compatible",
    "ollama",
    "vllm",
    "cpu_local",
    "deterministic_fallback_stub",
]

ModelProviderRole = Literal[
    "AGENT0_WAKE",
    "ORGAN_BACKGROUND",
    "ORGAN_HEAVY_REASONING",
    "AUTHORITY_ADVISORY",
    "CRITIQUE",
    "SUMMARY",
    "CODE_REVIEW",
    "STORAGE_RETRIEVAL_SUMMARY",
    "OPERATOR_EXPLANATION",
    "ROUTING_ADVISORY",
    "FALLBACK_STUB",
]

CostClass = Literal["local", "free", "cloud", "unknown"]
PrivacyClass = Literal["local", "private", "external"]

ProviderFailureReason = Literal[
    "DISABLED",
    "DISABLED_MISSING_SECRET",
    "DISABLED_EXTERNAL_NETWORK",
    "UNREACHABLE",
    "TIMEOUT",
    "FALLBACK_STUB_ONLY",
    "ROLE_NOT_ALLOWED",
    "DEFER_REVIEW",
    "PROVIDER_ERROR",
]

OpenVINOVerdict = Literal[
    "GREEN_REAL_OPENVINO_WINDOWS",
    "YELLOW_FALLBACK_STUB_ONLY",
    "YELLOW_PROVIDER_UNREACHABLE",
    "YELLOW_PROVIDER_CONTRACT_READY",
]


class ProviderCapability(str, Enum):
    CHAT = "chat"
    STREAMING = "streaming"
    HEALTH_PROBE = "health_probe"
    DEVICE_PROBE = "device_probe"
    CRITIQUE = "critique"
    SUMMARY = "summary"
    CODE_REVIEW = "code_review"


def advisory_envelope(**extra: Any) -> dict[str, Any]:
    base = {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "is_permit": False,
        "inference_is_advisory_only": True,
    }
    base.update(extra)
    if base.get("permission_granted") is True or base.get("authority_created") is True:
        raise ValueError("fabric must not grant permission or authority")
    return base


@dataclass(frozen=True)
class ProviderBudget:
    max_output_tokens: int = 256
    max_context_tokens: int = 4096
    max_requests_per_minute: int = 30
    max_cost_class: CostClass = "cloud"


@dataclass(frozen=True)
class ProviderRateLimit:
    requests_per_minute: int = 30
    tokens_per_minute: int = 8000


@dataclass(frozen=True)
class ProviderSecurityEnvelope:
    requires_secret: bool = False
    secret_env_var: str | None = None
    external_network_required: bool = False
    privacy_class: PrivacyClass = "local"
    data_policy: str = "advisory_only_no_training"


@dataclass(frozen=True)
class ModelProviderConfig:
    provider_id: str
    provider_type: ProviderType
    model_id: str
    role_allowlist: tuple[ModelProviderRole, ...]
    enabled: bool
    endpoint_url: str | None = None
    health_url: str | None = None
    devices_url: str | None = None
    device: str = "AUTO"
    timeout_seconds: int = 60
    max_context_tokens: int = 4096
    max_output_tokens: int = 256
    streaming_supported: bool = False
    cost_class: CostClass = "local"
    privacy_class: PrivacyClass = "local"
    data_policy: str = "advisory_only"
    fallback_priority: int = 100
    external_network_required: bool = False
    requires_secret: bool = False
    secret_env_var: str | None = None
    allow_fallback_stub: bool = False
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def __post_init__(self) -> None:
        if self.permission_granted or self.authority_created:
            raise ValueError("provider config must not grant permission or authority")
        if not self.advisory_only:
            raise ValueError("provider config must be advisory_only")

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="model-provider-config",
            schema_version=FABRIC_SCHEMA_VERSION,
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            model_id=self.model_id,
            endpoint_url=self.endpoint_url,
            health_url=self.health_url,
            devices_url=self.devices_url,
            device=self.device,
            role_allowlist=list(self.role_allowlist),
            enabled=self.enabled,
            timeout_seconds=self.timeout_seconds,
            max_context_tokens=self.max_context_tokens,
            max_output_tokens=self.max_output_tokens,
            streaming_supported=self.streaming_supported,
            cost_class=self.cost_class,
            privacy_class=self.privacy_class,
            data_policy=self.data_policy,
            fallback_priority=self.fallback_priority,
            external_network_required=self.external_network_required,
            requires_secret=self.requires_secret,
            secret_env_var=self.secret_env_var,
            allow_fallback_stub=self.allow_fallback_stub,
        )


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    reachable: bool
    healthy: bool
    model_loaded: bool = False
    resolved_device: str | None = None
    fallback_stub: bool = False
    openvino_verdict: OpenVINOVerdict | None = None
    failure_reason: ProviderFailureReason | None = None
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="provider-health",
            schema_version=FABRIC_SCHEMA_VERSION,
            provider_id=self.provider_id,
            reachable=self.reachable,
            healthy=self.healthy,
            model_loaded=self.model_loaded,
            resolved_device=self.resolved_device,
            fallback_stub=self.fallback_stub,
            openvino_verdict=self.openvino_verdict,
            failure_reason=self.failure_reason,
            detail=self.detail,
        )


@dataclass(frozen=True)
class ProviderSelectionRequest:
    role: ModelProviderRole
    organ_id: str | None = None
    request_id: str = "mpf:selection"
    risk_class: str = "normal"
    allow_fallback_stub: bool = False
    external_network_allowed: bool = False
    high_risk_authority_adjacent: bool = False

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="provider-selection-request",
            schema_version=FABRIC_SCHEMA_VERSION,
            role=self.role,
            organ_id=self.organ_id,
            request_id=self.request_id,
            risk_class=self.risk_class,
            allow_fallback_stub=self.allow_fallback_stub,
            external_network_allowed=self.external_network_allowed,
            high_risk_authority_adjacent=self.high_risk_authority_adjacent,
        )


@dataclass(frozen=True)
class ProviderSelectionDecision:
    request_id: str
    selected_provider_id: str | None
    selected_provider_type: ProviderType | None
    role: ModelProviderRole
    fallback_chain: tuple[str, ...]
    failure_reason: ProviderFailureReason | None = None
    deferred: bool = False
    rationale: str = ""

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="provider-selection-decision",
            schema_version=FABRIC_SCHEMA_VERSION,
            request_id=self.request_id,
            selected_provider_id=self.selected_provider_id,
            selected_provider_type=self.selected_provider_type,
            role=self.role,
            fallback_chain=list(self.fallback_chain),
            failure_reason=self.failure_reason,
            deferred=self.deferred,
            rationale=self.rationale,
        )


@dataclass(frozen=True)
class ProviderReceipt:
    receipt_id: str
    provider_id: str
    model_id: str
    role: ModelProviderRole
    organ_id: str | None
    request_id: str
    outcome: str
    fallback_stub: bool = False
    tokens_approx: int = 0
    observed_at: str = FIXTURE_CLOCK

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="provider-receipt",
            schema_version=FABRIC_SCHEMA_VERSION,
            receipt_id=self.receipt_id,
            provider_id=self.provider_id,
            model_id=self.model_id,
            role=self.role,
            organ_id=self.organ_id,
            request_id=self.request_id,
            outcome=self.outcome,
            fallback_stub=self.fallback_stub,
            tokens_approx=self.tokens_approx,
            observed_at=self.observed_at,
        )


@dataclass(frozen=True)
class OrganModelBinding:
    organ_id: str
    primary_role: ModelProviderRole
    secondary_roles: tuple[ModelProviderRole, ...] = ()
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="organ-model-binding",
            schema_version=FABRIC_SCHEMA_VERSION,
            organ_id=self.organ_id,
            primary_role=self.primary_role,
            secondary_roles=list(self.secondary_roles),
            notes=self.notes,
        )


@dataclass(frozen=True)
class AuthorityAdvisoryRequest:
    request_id: str
    evidence_summary: str
    deterministic_gate_state: str
    gpp_permit_present: bool
    permit_expired: bool
    operator_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="authority-advisory-request",
            schema_version=FABRIC_SCHEMA_VERSION,
            request_id=self.request_id,
            evidence_summary=self.evidence_summary,
            deterministic_gate_state=self.deterministic_gate_state,
            gpp_permit_present=self.gpp_permit_present,
            permit_expired=self.permit_expired,
            operator_ref=self.operator_ref,
        )


@dataclass(frozen=True)
class AuthorityAdvisoryResponse:
    request_id: str
    recommendation: str
    rationale: str
    contradictions: tuple[str, ...] = ()
    permit_candidate: bool = False

    def __post_init__(self) -> None:
        if self.recommendation.lower() in {"grant", "approved", "permit_granted", "execute"}:
            raise ValueError("authority advisory must not recommend direct grant")

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="authority-advisory-response",
            schema_version=FABRIC_SCHEMA_VERSION,
            request_id=self.request_id,
            recommendation=self.recommendation,
            rationale=self.rationale,
            contradictions=list(self.contradictions),
            permit_candidate=self.permit_candidate,
            model_may_not_grant_permission=True,
        )


@dataclass
class ModelProviderRegistry:
    providers: dict[str, ModelProviderConfig] = field(default_factory=dict)

    def register(self, config: ModelProviderConfig) -> None:
        self.providers[config.provider_id] = config

    def get(self, provider_id: str) -> ModelProviderConfig | None:
        return self.providers.get(provider_id)

    def enabled_for_role(self, role: ModelProviderRole) -> list[ModelProviderConfig]:
        return [
            p for p in self.providers.values()
            if p.enabled and role in p.role_allowlist
        ]

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="model-provider-registry",
            schema_version=FABRIC_SCHEMA_VERSION,
            providers=[p.to_payload() for p in self.providers.values()],
        )


__all__ = [
    "FABRIC_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "AuthorityAdvisoryRequest",
    "AuthorityAdvisoryResponse",
    "CostClass",
    "ModelProviderConfig",
    "ModelProviderRegistry",
    "ModelProviderRole",
    "OpenVINOVerdict",
    "OrganModelBinding",
    "PrivacyClass",
    "ProviderBudget",
    "ProviderCapability",
    "ProviderFailureReason",
    "ProviderHealth",
    "ProviderRateLimit",
    "ProviderReceipt",
    "ProviderSecurityEnvelope",
    "ProviderSelectionDecision",
    "ProviderSelectionRequest",
    "ProviderType",
    "advisory_envelope",
]
