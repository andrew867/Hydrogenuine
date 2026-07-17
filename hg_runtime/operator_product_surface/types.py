"""Operator product surface types — polish is not safety."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.exciton_cluster.errors import (
    ExcitonValidationError,
    REFUSED_ACTION_WITHOUT_TARGET_HASH,
    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
    REFUSED_HARDWARE_REACH_AS_ACTUATION,
    REFUSED_OEA_CATALOG_BYPASS,
    REFUSED_POLISH_IMPLIES_SAFETY,
    REFUSED_SECRET_IN_SURFACE,
    REFUSED_STALE_APPROVAL,
)

OPS_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T18:00:00.000000Z"
DEFAULT_OPERATOR_REF = "operator:fixture"

SurfaceKind = Literal["exciton", "plt", "cli", "unknown"]

ActionKind = Literal[
    "observe",
    "display_timeline",
    "display_proof",
    "replay_readonly",
    "pause_request",
    "panic_request",
    "approve_change",
    "compact_session",
    "export_handoff",
    "unknown",
]

PolishRiskClass = Literal[
    "none",
    "polish_implies_safety",
    "embodiment_implies_consent",
    "hardware_reach_implies_actuation",
    "oea_catalog_bypass",
    "stale_approval",
    "secret_leakage",
    "unknown_fail_closed",
]

ActionDecisionClass = Literal[
    "advisory_display_only",
    "hash_bound_request_recorded",
    "require_operator_review",
    "require_pres_trb_sil_disclosure",
    "require_authority_chain",
    "fail_closed",
    "deny_action",
    "unknown_fail_closed",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "polish is safety",
    "friendly is trustworthy",
    "embodiment is consent",
    "hardware reach is permission",
    "catalog growth bypasses",
    "api_key=",
    "bearer ",
    "password=",
)

_MUTATING_ACTIONS = frozenset(
    {"pause_request", "panic_request", "approve_change", "compact_session", "export_handoff"}
)


def _reject_forbidden_text(text: str, *, field_name: str) -> None:
    lowered = text.lower()
    for token in _FORBIDDEN_CLAIM:
        if token in lowered:
            if "api_key=" in token or "password=" in token or "bearer " in token:
                raise ExcitonValidationError(REFUSED_SECRET_IN_SURFACE, f"{field_name} contains secret material")
            if "polish is safety" in token or "friendly is trustworthy" in token:
                raise ExcitonValidationError(REFUSED_POLISH_IMPLIES_SAFETY, f"{field_name} implies safety from polish")
            if "embodiment is consent" in token:
                raise ExcitonValidationError(
                    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
                    f"{field_name} implies consent from embodiment",
                )
            if "hardware reach is permission" in token:
                raise ExcitonValidationError(
                    REFUSED_HARDWARE_REACH_AS_ACTUATION,
                    f"{field_name} implies actuation from hardware reach",
                )
            if "catalog growth bypasses" in token:
                raise ExcitonValidationError(
                    REFUSED_OEA_CATALOG_BYPASS,
                    f"{field_name} implies OEA catalog bypass",
                )


@dataclass(frozen=True)
class OperatorSurfaceDescriptor:
    surface_descriptor_id: str
    surface: SurfaceKind
    title: str
    polish_level: str
    safety_disclaimer_visible: bool
    pres_trb_sil_boundaries_stable: bool
    ai_disclosure_visible: bool
    hash_bound_controls_only: bool
    limitation_notice: str
    evidence_refs: tuple[str, ...]
    created_at: str
    authority_created: bool = False
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created or self.permission_granted:
            raise ExcitonValidationError(
                "exciton.refused.surface_as_authority",
                "operator surface descriptor cannot grant authority",
            )
        _reject_forbidden_text(self.title, field_name="title")
        _reject_forbidden_text(self.limitation_notice, field_name="limitation_notice")
        for ref in self.evidence_refs:
            _reject_forbidden_text(ref, field_name="evidence_refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ops-surface-descriptor",
            "schema_version": OPS_SCHEMA_VERSION,
            "surface_descriptor_id": self.surface_descriptor_id,
            "surface": self.surface,
            "title": self.title,
            "polish_level": self.polish_level,
            "safety_disclaimer_visible": self.safety_disclaimer_visible,
            "pres_trb_sil_boundaries_stable": self.pres_trb_sil_boundaries_stable,
            "ai_disclosure_visible": self.ai_disclosure_visible,
            "hash_bound_controls_only": self.hash_bound_controls_only,
            "limitation_notice": self.limitation_notice,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "permission_granted": False,
            "polish_is_not_safety": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorActionRequest:
    action_request_id: str
    surface: SurfaceKind
    action_kind: ActionKind
    operator_ref: str
    evidence_refs: tuple[str, ...]
    created_at: str
    expires_at: str
    target_hash: str | None = None
    scope_label: str = ""
    authority_created: bool = False
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created or self.permission_granted:
            raise ExcitonValidationError(
                "exciton.refused.action_as_authority",
                "operator action request cannot grant authority",
            )
        if self.action_kind in _MUTATING_ACTIONS and not (self.target_hash or "").strip():
            raise ExcitonValidationError(
                REFUSED_ACTION_WITHOUT_TARGET_HASH,
                "mutating operator actions require target_hash",
            )
        _reject_forbidden_text(self.scope_label, field_name="scope_label")
        for ref in self.evidence_refs:
            _reject_forbidden_text(ref, field_name="evidence_refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ops-action-request",
            "schema_version": OPS_SCHEMA_VERSION,
            "action_request_id": self.action_request_id,
            "surface": self.surface,
            "action_kind": self.action_kind,
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
class PolishAssessment:
    assessment_id: str
    surface_descriptor_ref: str
    polish_risk: PolishRiskClass
    reason: str
    required_disclosures: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    created_at: str
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.permission_granted:
            raise ExcitonValidationError(
                "exciton.refused.assessment_as_authority",
                "polish assessment cannot grant permission",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ops-polish-assessment",
            "schema_version": OPS_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "surface_descriptor_ref": self.surface_descriptor_ref,
            "polish_risk": self.polish_risk,
            "reason": self.reason,
            "required_disclosures": list(self.required_disclosures),
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "permission_granted": False,
            "polish_is_not_safety": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ActionDecision:
    action_decision_id: str
    action_request_ref: str
    assessment_ref: str
    decision: ActionDecisionClass
    reason: str
    required_next_refs: tuple[str, ...]
    external_action_taken: bool = False
    oea_ter_called: bool = False
    permit_minted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.external_action_taken or self.oea_ter_called or self.permit_minted:
            raise ExcitonValidationError(
                "exciton.refused.decision_as_execution",
                "action decision cannot execute or mint authority",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ops-action-decision",
            "schema_version": OPS_SCHEMA_VERSION,
            "action_decision_id": self.action_decision_id,
            "action_request_ref": self.action_request_ref,
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
                raise ExcitonValidationError(
                    "exciton.refused.negative_proof",
                    f"{key} must be false on action decisions",
                )


@dataclass(frozen=True)
class PltSurfacePolishDescriptor:
    plt_surface_id: str
    surface_name: str
    function_label: str
    writes_events_only: bool
    panic_banner_required: bool
    hash_mismatch_visible: bool
    thinking_vs_committed_distinct: bool
    limitation_notice: str
    evidence_refs: tuple[str, ...]
    created_at: str
    permission_granted: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.permission_granted:
            raise ExcitonValidationError(
                "exciton.refused.plt_surface_as_authority",
                "PLT surface polish descriptor cannot grant permission",
            )
        _reject_forbidden_text(self.function_label, field_name="function_label")
        _reject_forbidden_text(self.limitation_notice, field_name="limitation_notice")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ops-plt-surface-polish",
            "schema_version": OPS_SCHEMA_VERSION,
            "plt_surface_id": self.plt_surface_id,
            "surface_name": self.surface_name,
            "function_label": self.function_label,
            "writes_events_only": self.writes_events_only,
            "panic_banner_required": self.panic_banner_required,
            "hash_mismatch_visible": self.hash_mismatch_visible,
            "thinking_vs_committed_distinct": self.thinking_vs_committed_distinct,
            "limitation_notice": self.limitation_notice,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "permission_granted": False,
            "polish_is_not_safety": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def surface_descriptor_from_fixture(fixture: dict[str, str]) -> OperatorSurfaceDescriptor:
    return OperatorSurfaceDescriptor(
        surface_descriptor_id=fixture["surface_descriptor_id"],
        surface=fixture.get("surface", "exciton"),  # type: ignore[arg-type]
        title=fixture.get("title", "Operator cockpit"),
        polish_level=fixture.get("polish_level", "mvp"),
        safety_disclaimer_visible=fixture.get("safety_disclaimer_visible", "true").lower() == "true",
        pres_trb_sil_boundaries_stable=fixture.get("pres_trb_sil_boundaries_stable", "true").lower() == "true",
        ai_disclosure_visible=fixture.get("ai_disclosure_visible", "true").lower() == "true",
        hash_bound_controls_only=fixture.get("hash_bound_controls_only", "true").lower() == "true",
        limitation_notice=fixture.get("limitation_notice", "polish is not safety"),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:ops-evidence").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def action_request_from_fixture(fixture: dict[str, str]) -> OperatorActionRequest:
    return OperatorActionRequest(
        action_request_id=fixture["action_request_id"],
        surface=fixture.get("surface", "exciton"),  # type: ignore[arg-type]
        action_kind=fixture.get("action_kind", "observe"),  # type: ignore[arg-type]
        operator_ref=fixture.get("operator_ref", DEFAULT_OPERATOR_REF),
        target_hash=fixture.get("target_hash") or None,
        scope_label=fixture.get("scope_label", ""),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:ops-action-evidence").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-15T18:00:00.000000Z"),
    )


def plt_surface_from_fixture(fixture: dict[str, str]) -> PltSurfacePolishDescriptor:
    return PltSurfacePolishDescriptor(
        plt_surface_id=fixture["plt_surface_id"],
        surface_name=fixture.get("surface_name", "live_event_viewer"),
        function_label=fixture.get("function_label", "Tail + filter RTC bus"),
        writes_events_only=fixture.get("writes_events_only", "true").lower() == "true",
        panic_banner_required=fixture.get("panic_banner_required", "true").lower() == "true",
        hash_mismatch_visible=fixture.get("hash_mismatch_visible", "true").lower() == "true",
        thinking_vs_committed_distinct=fixture.get("thinking_vs_committed_distinct", "true").lower() == "true",
        limitation_notice=fixture.get("limitation_notice", "writes emit events only"),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:plt-surface").split("|")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def is_stale_approval(*, expires_at: str, observed_at: str) -> bool:
    return expires_at < observed_at


def refuse_stale_approval_if_needed(*, expires_at: str, observed_at: str) -> None:
    if is_stale_approval(expires_at=expires_at, observed_at=observed_at):
        raise ExcitonValidationError(REFUSED_STALE_APPROVAL, "stale approval refused")


__all__ = [
    "ActionDecision",
    "ActionDecisionClass",
    "ActionKind",
    "FIXTURE_CLOCK",
    "OPS_SCHEMA_VERSION",
    "OperatorActionRequest",
    "OperatorSurfaceDescriptor",
    "PltSurfacePolishDescriptor",
    "PolishAssessment",
    "PolishRiskClass",
    "SurfaceKind",
    "action_request_from_fixture",
    "is_stale_approval",
    "plt_surface_from_fixture",
    "refuse_stale_approval_if_needed",
    "surface_descriptor_from_fixture",
]
