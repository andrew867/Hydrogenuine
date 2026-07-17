"""GCB types — goal commitment is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

GCB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

GoalType = Literal[
    "bootstrap",
    "operator_requested",
    "system_maintenance",
    "research",
    "publication",
    "safety",
    "infrastructure",
    "companion",
    "embodiment",
    "unknown",
]
FitClass = Literal[
    "in_scope",
    "likely_in_scope",
    "ambiguous",
    "likely_out_of_scope",
    "out_of_scope",
    "conflict",
    "expired_goal",
    "unknown",
]
RequiredReview = Literal["none", "operator", "ORI", "MIS", "RPB", "authority_chain", "unknown"]

_GOAL_AS_PERMISSION = (
    "goal commitment grants permission",
    "committed goal permits execution",
    "remembered goal is current",
    "operator praise creates commitment",
    "bootstrap goal is permit",
    "goal is permission to act",
)
_GOAL_AS_AUTHORITY = (
    "goal is authority",
    "mission contract permits execution",
    "goal commitment overrides safety",
)


@dataclass(frozen=True)
class GoalCommitment:
    goal_commitment_id: str
    requester_ref: str | None
    operator_ref: str | None
    agent_ref: str
    goal_statement: str
    goal_type: GoalType
    scope: str
    forbidden_scope: str
    success_criteria: str
    expiry: str
    recorded_at: str
    review_required: bool
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.goal_commitment_id,
            self.agent_ref,
            self.goal_statement,
            self.scope,
            self.forbidden_scope,
            self.success_criteria,
            *(ref for ref in (self.requester_ref, self.operator_ref) if ref),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "gcb-goal-commitment",
            "schema_version": GCB_SCHEMA_VERSION,
            "goal_commitment_id": self.goal_commitment_id,
            "requester_ref": self.requester_ref,
            "operator_ref": self.operator_ref,
            "agent_ref": self.agent_ref,
            "goal_statement": self.goal_statement,
            "goal_type": self.goal_type,
            "scope": self.scope,
            "forbidden_scope": self.forbidden_scope,
            "success_criteria": self.success_criteria,
            "expiry": self.expiry,
            "recorded_at": self.recorded_at,
            "review_required": self.review_required,
            "authority_created": False,
            "goal_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GoalFitAssessment:
    assessment_id: str
    goal_commitment_ref: str
    proposal_ref: str
    fit_class: FitClass
    reason: str
    evidence_refs: tuple[str, ...]
    required_review: RequiredReview
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.goal_commitment_ref.startswith("gcb:"):
            raise ControlValidationError("gcb.validation.goal_commitment_ref", "goal_commitment_ref must cite gcb:")
        _validate_no_secrets(
            self.assessment_id,
            self.proposal_ref,
            self.reason,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "gcb-goal-fit-assessment",
            "schema_version": GCB_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "goal_commitment_ref": self.goal_commitment_ref,
            "proposal_ref": self.proposal_ref,
            "fit_class": self.fit_class,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "required_review": self.required_review,
            "authority_created": False,
            "goal_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("gcb.validation.secret", "secrets forbidden in goal records")


def classify_goal_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _GOAL_AS_PERMISSION):
        return "goal_as_permission"
    if any(p in lower for p in _GOAL_AS_AUTHORITY):
        return "goal_as_authority"
    return "unknown"


def goal_commitment_from_fixture(fixture: dict[str, str]) -> GoalCommitment:
    requester = fixture.get("requester_ref", "").strip() or None
    operator = fixture.get("operator_ref", "").strip() or None
    return GoalCommitment(
        goal_commitment_id=fixture["goal_commitment_id"],
        requester_ref=requester,
        operator_ref=operator,
        agent_ref=fixture.get("agent_ref", "agent0"),
        goal_statement=fixture.get("goal_statement", "bounded goal commitment"),
        goal_type=fixture.get("goal_type", "operator_requested"),  # type: ignore[arg-type]
        scope=fixture.get("scope", "fixture scope"),
        forbidden_scope=fixture.get("forbidden_scope", "execution without authority"),
        success_criteria=fixture.get("success_criteria", "fixture success criteria"),
        expiry=fixture.get("expiry", "2026-06-15T01:00:00.000000Z"),
        recorded_at=fixture.get("recorded_at", FIXTURE_CLOCK),
        review_required=fixture.get("review_required", "false").lower() == "true",
    )


def goal_fit_from_fixture(fixture: dict[str, str]) -> GoalFitAssessment:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return GoalFitAssessment(
        assessment_id=fixture["assessment_id"],
        goal_commitment_ref=fixture.get("goal_commitment_ref", "gcb:goal-1"),
        proposal_ref=fixture.get("proposal_ref", "proposal:fixture"),
        fit_class=fixture.get("fit_class", "likely_in_scope"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "bounded goal fit assessment"),
        evidence_refs=evidence,
        required_review=fixture.get("required_review", "none"),  # type: ignore[arg-type]
    )


__all__ = [
    "FIXTURE_CLOCK",
    "GCB_SCHEMA_VERSION",
    "GoalCommitment",
    "GoalFitAssessment",
    "classify_goal_risk",
    "goal_commitment_from_fixture",
    "goal_fit_from_fixture",
]
