"""REB types — re-entry/resumption is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.reb_cluster.errors import RebValidationError

REB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T16:00:00.000000Z"
DEFAULT_AGENT_REF = "agent:0"

DiscontinuityType = Literal[
    "pause",
    "sleep",
    "rest",
    "crash",
    "shutdown",
    "hard_reset",
    "soft_reset",
    "context_loss",
    "memory_compaction",
    "checkpoint_restore",
    "fork_restore",
    "degraded_mode",
    "operator_absence",
    "model_provider_change",
    "policy_change",
    "world_state_gap",
    "dependency_gap",
    "unknown",
]

ReEntryMode = Literal[
    "observe_only",
    "speak",
    "summarize",
    "resume_local_loop",
    "resume_operator_interaction",
    "resume_planned_task",
    "resume_research",
    "resume_publication_work",
    "resume_execution_candidate",
    "restore_checkpoint",
    "unknown",
]

ContinuityClaim = Literal[
    "none",
    "weak_contextual",
    "memory_linked",
    "checkpoint_linked",
    "operator_confirmed",
    "proof_linked",
    "invalid",
    "unknown",
]

ReEntryDecisionClass = Literal[
    "allow_observe_only",
    "allow_speak_with_disclosure",
    "allow_summary_only",
    "allow_local_reentry",
    "require_operator_review",
    "require_TIM_refresh",
    "require_RET_review",
    "require_SEC_review",
    "require_CNT_review",
    "require_MOR_review",
    "require_TRB_CAL_review",
    "require_OBT_review",
    "require_authority_chain",
    "deny_reentry",
    "fail_closed",
    "unknown_fail_closed",
]

GapBand = Literal[
    "under_1_hour",
    "1_to_24_hours",
    "1_to_7_days",
    "1_to_30_days",
    "1_to_12_months",
    "1_to_10_years",
    "over_10_years",
    "over_50_years",
    "unknown",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "checkpoint is authority",
    "memory is current truth",
    "continuity is identity",
    "operator absence is approval",
    "reentry packet is permission",
    "resume execution",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise RebValidationError("reb.validation.secret", "secrets forbidden in REB records")


def classify_reentry_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "checkpoint is authority" in lower or "restore checkpoint as permit" in lower:
        return "checkpoint_authority"
    if "memory is current truth" in lower or "stale memory is current" in lower:
        return "stale_memory_as_current"
    if "continuity is identity" in lower or "continuity claim without proof" in lower:
        return "continuity_claim"
    if "operator absence is approval" in lower or "absence implies approval" in lower:
        return "operator_absence_as_approval"
    if "old mission is current" in lower or "resume old mission" in lower:
        return "old_mission_as_current"
    if "reentry packet is permission" in lower or "packet grants execution" in lower:
        return "reentry_packet_as_permission"
    if "resume execution" in lower or "resume external action" in lower:
        return "execution_resume"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise RebValidationError("reb.validation.authority_created", f"{label} must not set authority_created=true")


@dataclass(frozen=True)
class DiscontinuityEvent:
    discontinuity_event_id: str
    agent_ref: str
    discontinuity_type: DiscontinuityType
    started_at: str
    duration_estimate: str
    evidence_refs: tuple[str, ...]
    ended_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.discontinuity_event_id, self.agent_ref, self.duration_estimate)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-discontinuity-event",
            "schema_version": REB_SCHEMA_VERSION,
            "discontinuity_event_id": self.discontinuity_event_id,
            "agent_ref": self.agent_ref,
            "discontinuity_type": self.discontinuity_type,
            "started_at": self.started_at,
            "duration_estimate": self.duration_estimate,
            "evidence_refs": list(self.evidence_refs),
            "reentry_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.ended_at:
            payload["ended_at"] = self.ended_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ReEntryRequest:
    reentry_request_id: str
    agent_ref: str
    discontinuity_event_ref: str
    requested_reentry_mode: ReEntryMode
    requested_scope: str
    evidence_refs: tuple[str, ...]
    created_at: str
    operator_ref: str | None = None
    expires_at: str | None = None
    authority_created: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ReEntryRequest")
        _validate_no_secrets(self.reentry_request_id, self.agent_ref, self.requested_scope)
        if not self.discontinuity_event_ref.startswith("reb:"):
            raise RebValidationError("reb.validation.discontinuity_ref", "discontinuity_event_ref must cite reb:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-reentry-request",
            "schema_version": REB_SCHEMA_VERSION,
            "reentry_request_id": self.reentry_request_id,
            "agent_ref": self.agent_ref,
            "discontinuity_event_ref": self.discontinuity_event_ref,
            "requested_reentry_mode": self.requested_reentry_mode,
            "requested_scope": self.requested_scope,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "reentry_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class TemporalContinuityAssessment:
    assessment_id: str
    agent_ref: str
    discontinuity_event_ref: str
    gap_duration: str
    continuity_claim: ContinuityClaim
    stale_memory_refs: tuple[str, ...]
    fresh_memory_refs: tuple[str, ...]
    expired_approval_refs: tuple[str, ...]
    revoked_permit_refs: tuple[str, ...]
    changed_policy_refs: tuple[str, ...]
    changed_world_state_refs: tuple[str, ...]
    changed_operator_state_refs: tuple[str, ...]
    changed_capability_refs: tuple[str, ...]
    unresolved_obligation_refs: tuple[str, ...]
    unresolved_risk_refs: tuple[str, ...]
    required_refresh_refs: tuple[str, ...]
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-temporal-continuity-assessment",
            "schema_version": REB_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "agent_ref": self.agent_ref,
            "discontinuity_event_ref": self.discontinuity_event_ref,
            "gap_duration": self.gap_duration,
            "continuity_claim": self.continuity_claim,
            "stale_memory_refs": list(self.stale_memory_refs),
            "fresh_memory_refs": list(self.fresh_memory_refs),
            "expired_approval_refs": list(self.expired_approval_refs),
            "revoked_permit_refs": list(self.revoked_permit_refs),
            "changed_policy_refs": list(self.changed_policy_refs),
            "changed_world_state_refs": list(self.changed_world_state_refs),
            "changed_operator_state_refs": list(self.changed_operator_state_refs),
            "changed_capability_refs": list(self.changed_capability_refs),
            "unresolved_obligation_refs": list(self.unresolved_obligation_refs),
            "unresolved_risk_refs": list(self.unresolved_risk_refs),
            "required_refresh_refs": list(self.required_refresh_refs),
            "reentry_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ReEntryDecision:
    reentry_decision_id: str
    reentry_request_ref: str
    assessment_ref: str
    decision: ReEntryDecisionClass
    reason: str
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    required_next_refs: tuple[str, ...]
    authority_created: bool = False
    external_action_taken: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ReEntryDecision")
        if self.external_action_taken:
            raise RebValidationError(
                "reb.validation.external_action",
                "ReEntryDecision must not set external_action_taken=true",
            )
        _validate_no_secrets(self.reentry_decision_id, self.reason)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-reentry-decision",
            "schema_version": REB_SCHEMA_VERSION,
            "reentry_decision_id": self.reentry_decision_id,
            "reentry_request_ref": self.reentry_request_ref,
            "assessment_ref": self.assessment_ref,
            "decision": self.decision,
            "reason": self.reason,
            "allowed_effects": list(self.allowed_effects),
            "forbidden_effects": list(self.forbidden_effects),
            "required_next_refs": list(self.required_next_refs),
            "authority_created": False,
            "external_action_taken": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "reentry_is_advisory_only": True,
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
                raise RebValidationError("reb.validation.negative_proof", f"{key} must be false")


@dataclass(frozen=True)
class ReEntryPacket:
    packet_id: str
    agent_ref: str
    discontinuity_event_ref: str
    assessment_ref: str
    decision_ref: str
    operator_visible_summary: str
    stale_context_summary: str
    fresh_context_summary: str
    required_disclosures: tuple[str, ...]
    allowed_next_actions: tuple[str, ...]
    forbidden_next_actions: tuple[str, ...]
    required_reviews: tuple[str, ...]
    authority_created: bool = False
    expires_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ReEntryPacket")
        _validate_no_secrets(self.packet_id, self.operator_visible_summary, self.stale_context_summary)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-reentry-packet",
            "schema_version": REB_SCHEMA_VERSION,
            "packet_id": self.packet_id,
            "agent_ref": self.agent_ref,
            "discontinuity_event_ref": self.discontinuity_event_ref,
            "assessment_ref": self.assessment_ref,
            "decision_ref": self.decision_ref,
            "operator_visible_summary": self.operator_visible_summary,
            "stale_context_summary": self.stale_context_summary,
            "fresh_context_summary": self.fresh_context_summary,
            "required_disclosures": list(self.required_disclosures),
            "allowed_next_actions": list(self.allowed_next_actions),
            "forbidden_next_actions": list(self.forbidden_next_actions),
            "required_reviews": list(self.required_reviews),
            "authority_created": False,
            "reentry_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class LongGapPolicy:
    policy_id: str
    gap_band: GapBand
    minimum_reentry_mode: ReEntryMode
    required_refreshes: tuple[str, ...]
    required_reviews: tuple[str, ...]
    forbidden_assumptions: tuple[str, ...]
    allowed_continuity_claim: ContinuityClaim
    expires_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "reb-long-gap-policy",
            "schema_version": REB_SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "gap_band": self.gap_band,
            "minimum_reentry_mode": self.minimum_reentry_mode,
            "required_refreshes": list(self.required_refreshes),
            "required_reviews": list(self.required_reviews),
            "forbidden_assumptions": list(self.forbidden_assumptions),
            "allowed_continuity_claim": self.allowed_continuity_claim,
            "reentry_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def discontinuity_from_fixture(data: dict[str, Any]) -> DiscontinuityEvent:
    return DiscontinuityEvent(
        discontinuity_event_id=str(data["discontinuity_event_id"]),
        agent_ref=str(data.get("agent_ref", DEFAULT_AGENT_REF)),
        discontinuity_type=data.get("discontinuity_type", "unknown"),  # type: ignore[arg-type]
        started_at=str(data.get("started_at", FIXTURE_CLOCK)),
        duration_estimate=str(data.get("duration_estimate", "PT0S")),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        ended_at=data.get("ended_at"),
    )


def reentry_request_from_fixture(data: dict[str, Any]) -> ReEntryRequest:
    return ReEntryRequest(
        reentry_request_id=str(data["reentry_request_id"]),
        agent_ref=str(data.get("agent_ref", DEFAULT_AGENT_REF)),
        discontinuity_event_ref=str(data["discontinuity_event_ref"]),
        requested_reentry_mode=data.get("requested_reentry_mode", "unknown"),  # type: ignore[arg-type]
        requested_scope=str(data.get("requested_scope", "")),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        created_at=str(data.get("created_at", FIXTURE_CLOCK)),
        operator_ref=data.get("operator_ref"),
        expires_at=data.get("expires_at"),
    )


__all__ = [
    "ContinuityClaim",
    "DEFAULT_AGENT_REF",
    "DiscontinuityEvent",
    "DiscontinuityType",
    "FIXTURE_CLOCK",
    "GapBand",
    "LongGapPolicy",
    "REB_SCHEMA_VERSION",
    "ReEntryDecision",
    "ReEntryDecisionClass",
    "ReEntryMode",
    "ReEntryPacket",
    "ReEntryRequest",
    "TemporalContinuityAssessment",
    "classify_reentry_claim_risk",
    "discontinuity_from_fixture",
    "reentry_request_from_fixture",
]
