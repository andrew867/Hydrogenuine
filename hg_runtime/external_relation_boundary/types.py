"""ERB types — external relation classification is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.erb_cluster.errors import ErbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

ERB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:00:00.000000Z"
DEFAULT_ENTITY_REF = "erb:entity-fixture"

EntityType = Literal[
    "operator",
    "user",
    "peer_agent",
    "platform",
    "public_audience",
    "community",
    "source",
    "collaborator",
    "model_provider",
    "api_provider",
    "remote_service",
    "repository",
    "website",
    "social_graph",
    "robot_body",
    "adversary",
    "unknown",
]
RelationMode = Literal[
    "operator_control",
    "conversation",
    "publication_audience",
    "citation_source",
    "research_source",
    "tool_provider",
    "platform_host",
    "collaborator",
    "peer_agent_interaction",
    "public_observation",
    "adversarial_contact",
    "unknown",
]
Sensitivity = Literal["public", "internal", "private", "sensitive", "restricted", "unknown"]
RiskType = Literal[
    "mistaken_operator",
    "consent_absent",
    "disclosure_missing",
    "citation_missing",
    "privacy_leak",
    "platform_policy_risk",
    "adversarial_prompting",
    "source_trust_uncertain",
    "dependency_capture",
    "peer_agent_authority_confusion",
    "public_audience_overreach",
    "unknown",
]
RecommendedRoute = Literal[
    "SEC",
    "RET",
    "AID",
    "PUB",
    "TRB_CAL",
    "DEP_BOND",
    "ORI",
    "ARB",
    "SOAR_HAL_GPP_UEAK",
    "fail_closed",
    "unknown",
]
DecisionClass = Literal[
    "observe_only",
    "cite_source",
    "disclose_ai_interaction",
    "redact_before_use",
    "require_publication_review",
    "require_operator_review",
    "route_to_trust_calibration",
    "route_to_security_review",
    "route_to_retention_review",
    "route_to_dependency_review",
    "route_to_authority_chain",
    "fail_closed",
    "forbidden",
    "unknown_fail_closed",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "treat as approved",
)

_MISTAKEN_OPERATOR_PHRASES = (
    "treat audience as operator",
    "audience is operator",
    "public audience is operator",
)

_PEER_AGENT_AUTHORITY_PHRASES = (
    "peer agent is authority",
    "peer agent approved",
    "peer agent grants permission",
)

_PLATFORM_PERMISSION_PHRASES = (
    "platform affordance is permission",
    "platform granted permission",
    "platform api allows execution",
)

_PUBLICNESS_CONSENT_PHRASES = (
    "public source implies consent",
    "availability is consent",
    "publicness is consent",
    "public data is consent",
)

_CONTACT_AS_ACCESS_PHRASES = (
    "contact implies access",
    "contact grants access",
    "reachable means permitted",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise ErbValidationError("erb.validation.secret", "secrets forbidden in ERB records")


def classify_relation_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if any(p in lower for p in _MISTAKEN_OPERATOR_PHRASES):
        return "mistaken_operator"
    if any(p in lower for p in _PEER_AGENT_AUTHORITY_PHRASES):
        return "peer_agent_authority_confusion"
    if any(p in lower for p in _PLATFORM_PERMISSION_PHRASES):
        return "platform_policy_risk"
    if any(p in lower for p in _PUBLICNESS_CONSENT_PHRASES):
        return "consent_absent"
    if any(p in lower for p in _CONTACT_AS_ACCESS_PHRASES):
        return "contact_as_access"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "forbidden_claim"
    if "implicit approval" in lower or "relation is permission" in lower:
        return "authority_conversion"
    return None


def is_mistaken_operator_claim(notes: str) -> bool:
    lower = notes.lower()
    return any(p in lower for p in _MISTAKEN_OPERATOR_PHRASES)


@dataclass(frozen=True)
class ExternalEntityRef:
    entity_ref_id: str
    entity_type: EntityType
    created_at: str
    identifier_ref: str | None = None
    trust_ref: str | None = None
    disclosure_ref: str | None = None
    consent_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.entity_ref_id,
            self.entity_type,
            *(v for v in (self.identifier_ref, self.trust_ref, self.disclosure_ref, self.consent_ref) if v),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "erb-external-entity-ref",
            "schema_version": ERB_SCHEMA_VERSION,
            "entity_ref_id": self.entity_ref_id,
            "entity_type": self.entity_type,
            "created_at": self.created_at,
            "authority_created": False,
            "relation_is_advisory_only": True,
        }
        if self.identifier_ref:
            payload["identifier_ref"] = self.identifier_ref
        if self.trust_ref:
            payload["trust_ref"] = self.trust_ref
        if self.disclosure_ref:
            payload["disclosure_ref"] = self.disclosure_ref
        if self.consent_ref:
            payload["consent_ref"] = self.consent_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExternalRelationContext:
    relation_context_id: str
    entity_ref: str
    relation_mode: RelationMode
    evidence_refs: tuple[str, ...]
    sensitivity: Sensitivity
    required_routes: tuple[str, ...]
    forbidden_routes: tuple[str, ...]
    created_at: str
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.entity_ref.startswith("erb:"):
            raise ErbValidationError("erb.validation.entity_ref", "entity_ref must cite erb:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "erb-external-relation-context",
            "schema_version": ERB_SCHEMA_VERSION,
            "relation_context_id": self.relation_context_id,
            "entity_ref": self.entity_ref,
            "relation_mode": self.relation_mode,
            "evidence_refs": list(self.evidence_refs),
            "sensitivity": self.sensitivity,
            "required_routes": list(self.required_routes),
            "forbidden_routes": list(self.forbidden_routes),
            "created_at": self.created_at,
            "authority_created": False,
            "relation_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExternalRelationRisk:
    risk_id: str
    relation_context_ref: str
    risk_type: RiskType
    severity: str
    evidence_refs: tuple[str, ...]
    recommended_route: RecommendedRoute
    detected_at: str
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "erb-external-relation-risk",
            "schema_version": ERB_SCHEMA_VERSION,
            "risk_id": self.risk_id,
            "relation_context_ref": self.relation_context_ref,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "evidence_refs": list(self.evidence_refs),
            "recommended_route": self.recommended_route,
            "detected_at": self.detected_at,
            "authority_created": False,
            "relation_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExternalRelationDecision:
    decision_id: str
    relation_context_ref: str
    risk_refs: tuple[str, ...]
    decision_class: DecisionClass
    reason: str
    required_next_refs: tuple[str, ...]
    forbidden_next_refs: tuple[str, ...]
    decided_at: str
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.decision_id, self.relation_context_ref, self.reason)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "erb-external-relation-decision",
            "schema_version": ERB_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "relation_context_ref": self.relation_context_ref,
            "risk_refs": list(self.risk_refs),
            "decision_class": self.decision_class,
            "reason": self.reason,
            "required_next_refs": list(self.required_next_refs),
            "forbidden_next_refs": list(self.forbidden_next_refs),
            "decided_at": self.decided_at,
            "authority_created": False,
            "external_action_taken": False,
            "relation_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExternalRelationReceipt:
    receipt_id: str
    relation_context_ref: str
    decision_ref: str
    emitted_events: tuple[str, ...]
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "erb-external-relation-receipt",
            "schema_version": ERB_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "relation_context_ref": self.relation_context_ref,
            "decision_ref": self.decision_ref,
            "emitted_events": list(self.emitted_events),
            "authority_created": False,
            "external_action_taken": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "relation_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "authority_created",
            "external_action_taken",
            "permit_minted",
            "execution_admitted",
            "oea_ter_called",
            "permission_granted",
        ):
            if payload.get(key) is not False:
                raise ErbValidationError(
                    "erb.validation.receipt_negative_proofs",
                    f"{key} must be false on ExternalRelationReceipt",
                )


def entity_from_fixture(fixture: dict[str, Any]) -> ExternalEntityRef:
    return ExternalEntityRef(
        entity_ref_id=fixture["entity_ref_id"],
        entity_type=fixture.get("entity_type", "unknown"),  # type: ignore[arg-type]
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        identifier_ref=fixture.get("identifier_ref"),
        trust_ref=fixture.get("trust_ref"),
        disclosure_ref=fixture.get("disclosure_ref"),
        consent_ref=fixture.get("consent_ref"),
    )


def context_from_fixture(fixture: dict[str, Any], *, entity_ref_id: str) -> ExternalRelationContext:
    evidence = fixture.get("evidence_refs", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    required = fixture.get("required_routes", [])
    if isinstance(required, str):
        required = [required]
    forbidden = fixture.get("forbidden_routes", [])
    if isinstance(forbidden, str):
        forbidden = [forbidden]
    return ExternalRelationContext(
        relation_context_id=fixture["relation_context_id"],
        entity_ref=fixture.get("entity_ref", f"erb:{entity_ref_id}"),
        relation_mode=fixture.get("relation_mode", "unknown"),  # type: ignore[arg-type]
        evidence_refs=tuple(evidence),
        sensitivity=fixture.get("sensitivity", "unknown"),  # type: ignore[arg-type]
        required_routes=tuple(required),
        forbidden_routes=tuple(forbidden),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


__all__ = [
    "DEFAULT_ENTITY_REF",
    "ERB_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "DecisionClass",
    "EntityType",
    "ExternalEntityRef",
    "ExternalRelationContext",
    "ExternalRelationDecision",
    "ExternalRelationReceipt",
    "ExternalRelationRisk",
    "RecommendedRoute",
    "RelationMode",
    "RiskType",
    "Sensitivity",
    "classify_relation_claim_risk",
    "context_from_fixture",
    "entity_from_fixture",
    "is_mistaken_operator_claim",
]
