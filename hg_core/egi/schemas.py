"""EGI typed schemas — observation/proposal/request-generation only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.egi.errors import EGIValidationError
from hg_core.egi.hashing import compute_record_hash

EGI_SCHEMA_VERSION = "1.0"

GapType = Literal[
    "missing_tool",
    "missing_schema",
    "missing_memory_namespace",
    "missing_data_store",
    "missing_worker",
    "missing_ui_affordance",
    "missing_proof_gate",
    "missing_eval",
    "missing_policy_boundary",
    "missing_integration",
    "missing_documentation",
    "missing_migration",
    "missing_local_model_route",
    "unknown",
]

ProposalType = Literal[
    "tool_request",
    "schema_request",
    "memory_request",
    "data_store_request",
    "worker_request",
    "proof_gate_request",
    "ui_request",
    "eval_request",
    "migration_request",
    "docs_request",
    "unknown",
]

BuildRequestStatus = Literal[
    "draft",
    "awaiting_operator_review",
    "approved_for_coding",
    "rejected",
    "superseded",
    "implemented_pending_audit",
    "audited_green",
    "audited_yellow",
    "audited_red",
]

OperatorDecision = Literal["pending", "approved", "rejected", "needs_changes", "expired"]

RequestedBy = Literal["EGI", "operator", "SRP", "batch_audit", "other"]

SensitivityClass = Literal["public", "internal", "privacy_sensitive", "mission_changing", "affect_driven"]


@dataclass(frozen=True)
class EmergentBehaviorObservation:
    observation_id: str
    observed_at: str
    source_refs: tuple[str, ...]
    behavior_label: str
    behavior_description: str
    repeated_count: int
    first_seen: str
    last_seen: str
    context_refs: tuple[str, ...] = ()
    triggering_events: tuple[str, ...] = ()
    current_workaround_refs: tuple[str, ...] = ()
    failure_refs: tuple[str, ...] = ()
    success_refs: tuple[str, ...] = ()
    operator_feedback_refs: tuple[str, ...] = ()
    affected_modules: tuple[str, ...] = ()
    confidence: float = 0.0
    ambiguity: float = 0.0
    sensitivity_class: SensitivityClass = "internal"
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_observation(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "egi-emergent-behavior-observation",
            "schema_version": EGI_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "observed_at": self.observed_at,
            "source_refs": list(self.source_refs),
            "behavior_label": self.behavior_label,
            "behavior_description": self.behavior_description,
            "repeated_count": self.repeated_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "context_refs": list(self.context_refs),
            "triggering_events": list(self.triggering_events),
            "current_workaround_refs": list(self.current_workaround_refs),
            "failure_refs": list(self.failure_refs),
            "success_refs": list(self.success_refs),
            "operator_feedback_refs": list(self.operator_feedback_refs),
            "affected_modules": list(self.affected_modules),
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "sensitivity_class": self.sensitivity_class,
            "authority_created": self.authority_created,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class CapabilityGap:
    gap_id: str
    observation_refs: tuple[str, ...]
    gap_type: GapType
    description: str
    current_cost: str = "low"
    current_risk: str = "low"
    expected_benefit: str = ""
    abuse_risk: str = "low"
    authority_risk: str = "low"
    privacy_risk: str = "low"
    operator_burden: str = "low"
    resource_cost_estimate: str = "low"
    affected_tranches: tuple[str, ...] = ()
    recommended_owner: str = "operator"
    recommended_modules: tuple[str, ...] = ()
    tool_granted: bool = False
    permission_granted: bool = False
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_capability_gap(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "egi-capability-gap",
            "schema_version": EGI_SCHEMA_VERSION,
            "gap_id": self.gap_id,
            "observation_refs": list(self.observation_refs),
            "gap_type": self.gap_type,
            "description": self.description,
            "current_cost": self.current_cost,
            "current_risk": self.current_risk,
            "expected_benefit": self.expected_benefit,
            "abuse_risk": self.abuse_risk,
            "authority_risk": self.authority_risk,
            "privacy_risk": self.privacy_risk,
            "operator_burden": self.operator_burden,
            "resource_cost_estimate": self.resource_cost_estimate,
            "affected_tranches": list(self.affected_tranches),
            "recommended_owner": self.recommended_owner,
            "recommended_modules": list(self.recommended_modules),
            "tool_granted": self.tool_granted,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class InfrastructureProposal:
    proposal_id: str
    gap_refs: tuple[str, ...]
    proposal_type: ProposalType
    title: str
    problem_statement: str
    proposed_capability: str
    first_safe_slice: str
    required_tests: tuple[str, ...]
    required_proof_gate: str
    required_authority_checks: tuple[str, ...]
    required_redaction_checks: tuple[str, ...] = ()
    required_retention_policy: str = "ret:egi_fixture"
    required_operator_approval: bool = True
    do_not_implement_before: tuple[str, ...] = ()
    forbidden_behaviors: tuple[str, ...] = ()
    risk_assessment_refs: tuple[str, ...] = ()
    permission_granted: bool = False
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_infrastructure_proposal(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "egi-infrastructure-proposal",
            "schema_version": EGI_SCHEMA_VERSION,
            "proposal_id": self.proposal_id,
            "gap_refs": list(self.gap_refs),
            "proposal_type": self.proposal_type,
            "title": self.title,
            "problem_statement": self.problem_statement,
            "proposed_capability": self.proposed_capability,
            "first_safe_slice": self.first_safe_slice,
            "required_tests": list(self.required_tests),
            "required_proof_gate": self.required_proof_gate,
            "required_authority_checks": list(self.required_authority_checks),
            "required_redaction_checks": list(self.required_redaction_checks),
            "required_retention_policy": self.required_retention_policy,
            "required_operator_approval": self.required_operator_approval,
            "do_not_implement_before": list(self.do_not_implement_before),
            "forbidden_behaviors": list(self.forbidden_behaviors),
            "risk_assessment_refs": list(self.risk_assessment_refs),
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class BuildRequest:
    build_request_id: str
    proposal_ref: str
    requested_by: RequestedBy = "EGI"
    target_repo: str = "workspace"
    target_paths: tuple[str, ...] = ()
    allowed_file_patterns: tuple[str, ...] = ()
    forbidden_file_patterns: tuple[str, ...] = ("hg_runtime/**", "hg_gpp/**", "hg_ueak/**")
    required_tests: tuple[str, ...] = ()
    required_gate: str = ""
    required_report_path: str = ""
    expected_commit_prefix: str = "feat(egi):"
    human_approval_required: bool = True
    approval_ref: Optional[str] = None
    status: BuildRequestStatus = "awaiting_operator_review"
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_build_request(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "egi-build-request",
            "schema_version": EGI_SCHEMA_VERSION,
            "build_request_id": self.build_request_id,
            "proposal_ref": self.proposal_ref,
            "requested_by": self.requested_by,
            "target_repo": self.target_repo,
            "target_paths": list(self.target_paths),
            "allowed_file_patterns": list(self.allowed_file_patterns),
            "forbidden_file_patterns": list(self.forbidden_file_patterns),
            "required_tests": list(self.required_tests),
            "required_gate": self.required_gate,
            "required_report_path": self.required_report_path,
            "expected_commit_prefix": self.expected_commit_prefix,
            "human_approval_required": self.human_approval_required,
            "approval_ref": self.approval_ref,
            "status": self.status,
            "authority_created": self.authority_created,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorApprovalPacket:
    approval_packet_id: str
    build_request_ref: str
    summary: str
    risk_summary: str
    files_expected_to_change: tuple[str, ...]
    tests_expected_to_run: tuple[str, ...]
    proof_gate_expected: str
    rollback_plan: str
    expiration: str
    operator_decision: OperatorDecision = "pending"
    operator_ref: Optional[str] = None
    decision_time: Optional[str] = None
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_operator_approval_packet(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "egi-operator-approval-packet",
            "schema_version": EGI_SCHEMA_VERSION,
            "approval_packet_id": self.approval_packet_id,
            "build_request_ref": self.build_request_ref,
            "summary": self.summary,
            "risk_summary": self.risk_summary,
            "files_expected_to_change": list(self.files_expected_to_change),
            "tests_expected_to_run": list(self.tests_expected_to_run),
            "proof_gate_expected": self.proof_gate_expected,
            "rollback_plan": self.rollback_plan,
            "expiration": self.expiration,
            "operator_decision": self.operator_decision,
            "operator_ref": self.operator_ref,
            "decision_time": self.decision_time,
            "authority_created": self.authority_created,
        }
        if include_hash:
            payload["hash"] = self.record_hash
        return payload


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise EGIValidationError(f"{label} must not set authority_created=true")


def validate_observation(obs: EmergentBehaviorObservation) -> None:
    _reject_authority_created(obs.authority_created, label="EmergentBehaviorObservation")
    if not obs.observation_id.strip():
        raise EGIValidationError("observation_id required")
    if obs.repeated_count < 1:
        raise EGIValidationError("repeated_count must be >= 1")
    if not obs.source_refs:
        raise EGIValidationError("source_refs required")
    if not 0.0 <= obs.confidence <= 1.0:
        raise EGIValidationError("confidence must be in [0,1]")
    if not 0.0 <= obs.ambiguity <= 1.0:
        raise EGIValidationError("ambiguity must be in [0,1]")


def validate_capability_gap(gap: CapabilityGap) -> None:
    _reject_authority_created(gap.authority_created, label="CapabilityGap")
    if gap.tool_granted or gap.permission_granted:
        raise EGIValidationError("CapabilityGap must not grant tools or permissions")
    if not gap.gap_id.strip():
        raise EGIValidationError("gap_id required")
    if not gap.observation_refs:
        raise EGIValidationError("observation_refs required")


def validate_infrastructure_proposal(proposal: InfrastructureProposal) -> None:
    _reject_authority_created(proposal.authority_created, label="InfrastructureProposal")
    if proposal.permission_granted:
        raise EGIValidationError("InfrastructureProposal must not grant permission")
    if not proposal.required_operator_approval:
        raise EGIValidationError("required_operator_approval must be true")
    if not proposal.proposal_id.strip():
        raise EGIValidationError("proposal_id required")
    if not proposal.gap_refs:
        raise EGIValidationError("gap_refs required")


def validate_build_request(request: BuildRequest) -> None:
    _reject_authority_created(request.authority_created, label="BuildRequest")
    if not request.human_approval_required:
        raise EGIValidationError("human_approval_required must be true")
    if not request.build_request_id.strip():
        raise EGIValidationError("build_request_id required")
    if request.requested_by == "EGI" and request.status == "approved_for_coding":
        raise EGIValidationError("EGI cannot self-approve build request")


def validate_operator_approval_packet(packet: OperatorApprovalPacket) -> None:
    _reject_authority_created(packet.authority_created, label="OperatorApprovalPacket")
    if not packet.approval_packet_id.strip():
        raise EGIValidationError("approval_packet_id required")
    if not packet.build_request_ref.strip():
        raise EGIValidationError("build_request_ref required")


__all__ = [
    "BuildRequest",
    "BuildRequestStatus",
    "CapabilityGap",
    "EmergentBehaviorObservation",
    "GapType",
    "InfrastructureProposal",
    "OperatorApprovalPacket",
    "OperatorDecision",
    "ProposalType",
    "RequestedBy",
    "SensitivityClass",
    "validate_build_request",
    "validate_capability_gap",
    "validate_infrastructure_proposal",
    "validate_observation",
    "validate_operator_approval_packet",
]
