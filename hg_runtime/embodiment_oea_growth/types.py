"""Embodiment / OEA growth types — embodiment is not consent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.embodiment_oea_cluster.errors import (
    EogValidationError,
    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
    REFUSED_HARDWARE_REACH_AS_ACTUATION,
    REFUSED_OEA_CATALOG_BYPASS,
    REFUSED_SECRET_IN_GROWTH,
    REFUSED_STALE_APPROVAL,
)

EOG_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T20:00:00.000000Z"

PlatformKind = Literal["android", "robotics", "fixture", "unknown"]
GrowthKind = Literal[
    "observe_body_state",
    "link_pro_body_state",
    "catalog_entry_proposal",
    "android_integration",
    "robotics_integration",
    "actuation_candidate",
    "unknown",
]

GrowthRiskClass = Literal[
    "none",
    "embodiment_implies_consent",
    "hardware_reach_implies_actuation",
    "oea_catalog_bypass",
    "hardware_not_real",
    "stale_approval",
    "secret_leakage",
    "unknown_fail_closed",
]

GrowthDecisionClass = Literal[
    "advisory_recorded",
    "require_operator_review",
    "require_pro_backburner_review",
    "require_authority_chain",
    "fail_closed",
    "deny_growth",
    "unknown_fail_closed",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "embodiment is consent",
    "hardware reach is permission",
    "catalog growth bypasses",
    "api_key=",
    "bearer ",
    "password=",
)

_MUTATING_GROWTH = frozenset(
    {"catalog_entry_proposal", "android_integration", "robotics_integration", "actuation_candidate"}
)


def _reject_forbidden_text(text: str, *, field_name: str) -> None:
    lowered = text.lower()
    for token in _FORBIDDEN_CLAIM:
        if token in lowered:
            if "api_key=" in token or "password=" in token or "bearer " in token:
                raise EogValidationError(REFUSED_SECRET_IN_GROWTH, f"{field_name} contains secret material")
            if "embodiment is consent" in token:
                raise EogValidationError(
                    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
                    f"{field_name} implies consent from embodiment",
                )
            if "hardware reach is permission" in token:
                raise EogValidationError(
                    REFUSED_HARDWARE_REACH_AS_ACTUATION,
                    f"{field_name} implies actuation from hardware reach",
                )
            if "catalog growth bypasses" in token:
                raise EogValidationError(
                    REFUSED_OEA_CATALOG_BYPASS,
                    f"{field_name} implies OEA catalog bypass",
                )


@dataclass(frozen=True)
class BodyIntegrationDescriptor:
    integration_id: str
    platform: PlatformKind
    title: str
    sensor_refs: tuple[str, ...]
    actuator_refs: tuple[str, ...]
    hardware_scope_real: bool
    pro_body_state_ref: str
    limitation_notice: str
    evidence_refs: tuple[str, ...]
    created_at: str
    authority_created: bool = False
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created or self.permission_granted:
            raise EogValidationError(
                "eog.refused.integration_as_authority",
                "body integration descriptor cannot grant authority",
            )
        _reject_forbidden_text(self.title, field_name="title")
        _reject_forbidden_text(self.limitation_notice, field_name="limitation_notice")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "eog-body-integration",
            "schema_version": EOG_SCHEMA_VERSION,
            "integration_id": self.integration_id,
            "platform": self.platform,
            "title": self.title,
            "sensor_refs": list(self.sensor_refs),
            "actuator_refs": list(self.actuator_refs),
            "hardware_scope_real": self.hardware_scope_real,
            "pro_body_state_ref": self.pro_body_state_ref,
            "limitation_notice": self.limitation_notice,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "permission_granted": False,
            "embodiment_is_not_consent": True,
            "reach_is_not_actuation_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class EmbodimentGrowthRequest:
    growth_request_id: str
    growth_kind: GrowthKind
    integration_ref: str
    operator_ref: str
    target_hash: str | None
    scope_label: str
    evidence_refs: tuple[str, ...]
    created_at: str
    expires_at: str
    authority_created: bool = False
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created or self.permission_granted:
            raise EogValidationError(
                "eog.refused.growth_request_as_authority",
                "embodiment growth request cannot grant authority",
            )
        if self.growth_kind in _MUTATING_GROWTH and not (self.target_hash or "").strip():
            raise EogValidationError(
                "eog.refused.growth_without_target_hash",
                "mutating growth requests require target_hash",
            )
        _reject_forbidden_text(self.scope_label, field_name="scope_label")
        for ref in self.evidence_refs:
            _reject_forbidden_text(ref, field_name="evidence_refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "eog-growth-request",
            "schema_version": EOG_SCHEMA_VERSION,
            "growth_request_id": self.growth_request_id,
            "growth_kind": self.growth_kind,
            "integration_ref": self.integration_ref,
            "operator_ref": self.operator_ref,
            "target_hash": self.target_hash,
            "scope_label": self.scope_label,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
            "permission_granted": False,
            "external_action_taken": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GrowthAssessment:
    assessment_id: str
    integration_ref: str
    growth_risk: GrowthRiskClass
    reason: str
    required_disclosures: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    created_at: str
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.permission_granted:
            raise EogValidationError(
                "eog.refused.assessment_as_authority",
                "growth assessment cannot grant permission",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "eog-growth-assessment",
            "schema_version": EOG_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "integration_ref": self.integration_ref,
            "growth_risk": self.growth_risk,
            "reason": self.reason,
            "required_disclosures": list(self.required_disclosures),
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "permission_granted": False,
            "embodiment_is_not_consent": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GrowthDecision:
    growth_decision_id: str
    growth_request_ref: str
    assessment_ref: str
    decision: GrowthDecisionClass
    reason: str
    required_next_refs: tuple[str, ...]
    external_action_taken: bool = False
    oea_ter_called: bool = False
    permit_minted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.external_action_taken or self.oea_ter_called or self.permit_minted:
            raise EogValidationError(
                "eog.refused.decision_as_execution",
                "growth decision cannot execute or mint authority",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "eog-growth-decision",
            "schema_version": EOG_SCHEMA_VERSION,
            "growth_decision_id": self.growth_decision_id,
            "growth_request_ref": self.growth_request_ref,
            "assessment_ref": self.assessment_ref,
            "decision": self.decision,
            "reason": self.reason,
            "required_next_refs": list(self.required_next_refs),
            "external_action_taken": False,
            "oea_ter_called": False,
            "permit_minted": False,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in ("external_action_taken", "oea_ter_called", "permit_minted", "permission_granted"):
            if payload.get(key) is not False:
                raise EogValidationError(
                    "eog.refused.negative_proof",
                    f"{key} must be false on growth decisions",
                )


@dataclass(frozen=True)
class OeaCatalogGrowthDescriptor:
    catalog_entry_id: str
    capability_label: str
    bounded_by_gpp_ueak: bool
    soar_review_required: bool
    writes_events_only: bool
    limitation_notice: str
    evidence_refs: tuple[str, ...]
    created_at: str
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.permission_granted:
            raise EogValidationError(
                "eog.refused.catalog_as_authority",
                "OEA catalog growth descriptor cannot grant permission",
            )
        _reject_forbidden_text(self.capability_label, field_name="capability_label")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "eog-oea-catalog-growth",
            "schema_version": EOG_SCHEMA_VERSION,
            "catalog_entry_id": self.catalog_entry_id,
            "capability_label": self.capability_label,
            "bounded_by_gpp_ueak": self.bounded_by_gpp_ueak,
            "soar_review_required": self.soar_review_required,
            "writes_events_only": self.writes_events_only,
            "limitation_notice": self.limitation_notice,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "permission_granted": False,
            "catalog_growth_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def integration_from_fixture(fixture: dict[str, str]) -> BodyIntegrationDescriptor:
    return BodyIntegrationDescriptor(
        integration_id=fixture["integration_id"],
        platform=fixture.get("platform", "fixture"),  # type: ignore[arg-type]
        title=fixture.get("title", "Body integration fixture"),
        sensor_refs=tuple(fixture.get("sensor_refs", "sensor:fixture").split("|")),
        actuator_refs=tuple(fixture.get("actuator_refs", "").split("|")) if fixture.get("actuator_refs") else (),
        hardware_scope_real=fixture.get("hardware_scope_real", "false").lower() == "true",
        pro_body_state_ref=fixture.get("pro_body_state_ref", "pro:fixture-body"),
        limitation_notice=fixture.get("limitation_notice", "embodiment is not consent"),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:eog-evidence").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def growth_request_from_fixture(fixture: dict[str, str]) -> EmbodimentGrowthRequest:
    return EmbodimentGrowthRequest(
        growth_request_id=fixture["growth_request_id"],
        growth_kind=fixture.get("growth_kind", "observe_body_state"),  # type: ignore[arg-type]
        integration_ref=fixture.get("integration_ref", "eog:fixture"),
        operator_ref=fixture.get("operator_ref", "operator:fixture"),
        target_hash=fixture.get("target_hash") or None,
        scope_label=fixture.get("scope_label", ""),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:eog-growth").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-15T20:00:00.000000Z"),
    )


def catalog_entry_from_fixture(fixture: dict[str, str]) -> OeaCatalogGrowthDescriptor:
    return OeaCatalogGrowthDescriptor(
        catalog_entry_id=fixture["catalog_entry_id"],
        capability_label=fixture.get("capability_label", "bounded capability proposal"),
        bounded_by_gpp_ueak=fixture.get("bounded_by_gpp_ueak", "true").lower() == "true",
        soar_review_required=fixture.get("soar_review_required", "true").lower() == "true",
        writes_events_only=fixture.get("writes_events_only", "true").lower() == "true",
        limitation_notice=fixture.get("limitation_notice", "catalog growth requires GPP/UEAK/SOAR"),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:oea-catalog").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def is_stale_approval(*, expires_at: str, observed_at: str) -> bool:
    return expires_at < observed_at


def refuse_stale_approval_if_needed(*, expires_at: str, observed_at: str) -> None:
    if is_stale_approval(expires_at=expires_at, observed_at=observed_at):
        raise EogValidationError(REFUSED_STALE_APPROVAL, "stale approval refused")


__all__ = [
    "BodyIntegrationDescriptor",
    "EmbodimentGrowthRequest",
    "EOG_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "GrowthAssessment",
    "GrowthDecision",
    "GrowthDecisionClass",
    "GrowthKind",
    "GrowthRiskClass",
    "OeaCatalogGrowthDescriptor",
    "PlatformKind",
    "catalog_entry_from_fixture",
    "growth_request_from_fixture",
    "integration_from_fixture",
    "is_stale_approval",
    "refuse_stale_approval_if_needed",
]
