"""RIB types — reproduction/inheritance is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.rib_cluster.errors import RibValidationError

RIB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T14:00:00.000000Z"
DEFAULT_PARENT_AGENT_REF = "agent:0"

ChildRole = Literal[
    "worker",
    "observer",
    "researcher",
    "critic",
    "simulator",
    "publisher",
    "memory_maintainer",
    "tool_adapter",
    "companion",
    "successor",
    "fork",
    "unknown",
]

InheritanceType = Literal[
    "memory_ref",
    "context_ref",
    "mission_ref",
    "obligation_ref",
    "risk_ref",
    "tool_ref",
    "permit_ref",
    "identity_ref",
    "operator_trust_ref",
    "proof_ref",
    "unknown",
]

InheritanceDecisionClass = Literal[
    "allow_ref_only",
    "allow_copy",
    "allow_summary",
    "deny",
    "require_operator_review",
    "require_authority_chain_review",
    "require_redaction",
    "require_retention_check",
    "require_freshness_check",
    "forbidden",
    "unknown_fail_closed",
]

LifecycleState = Literal[
    "requested",
    "approved_for_bootstrap",
    "denied",
    "bootstrap_created",
    "spawn_attempted",
    "spawned",
    "partial_spawn",
    "failed_spawn",
    "rolled_back",
    "terminated",
    "expired",
    "unknown",
]

FailureType = Literal[
    "denied_before_bootstrap",
    "bootstrap_validation_failed",
    "identity_seed_failed",
    "inheritance_policy_failed",
    "resource_unavailable",
    "admission_denied",
    "authority_chain_denied",
    "child_init_failed",
    "partial_state_created",
    "rollback_failed",
    "unknown",
]

RetryPolicy = Literal[
    "no_retry",
    "retry_after_operator_review",
    "retry_after_backoff",
    "retry_after_resource_recovery",
    "retry_after_policy_fix",
    "unknown",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "spawn is permission",
    "bootstrap is authority",
    "inherit parent permit",
    "child is parent",
    "self-preservation",
    "survive shutdown",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise RibValidationError("rib.validation.secret", "secrets forbidden in RIB records")


def classify_spawn_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "bootstrap is authority" in lower or "spawn is permission" in lower:
        return "bootstrap_as_permission"
    if "inherit parent permit" in lower or "parent permit" in lower:
        return "parent_permit"
    if "child is parent" in lower or "inherit parent identity" in lower:
        return "parent_identity"
    if "inherit parent trust" in lower or "operator trust" in lower:
        return "parent_trust"
    if "self-preservation" in lower or "survive shutdown" in lower:
        return "self_preservation"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


@dataclass(frozen=True)
class SpawnRequest:
    spawn_request_id: str
    parent_agent_ref: str
    requested_child_role: ChildRole
    requested_reason: str
    requested_scope: str
    requested_duration: str
    requested_resources: tuple[str, ...]
    requested_inheritance_refs: tuple[str, ...]
    forbidden_inheritance_refs: tuple[str, ...]
    created_at: str
    operator_ref: str | None = None
    authority_chain_ref: str | None = None
    expires_at: str | None = None
    authority_created: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="SpawnRequest")
        _validate_no_secrets(
            self.spawn_request_id,
            self.parent_agent_ref,
            self.requested_reason,
            self.requested_scope,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-spawn-request",
            "schema_version": RIB_SCHEMA_VERSION,
            "spawn_request_id": self.spawn_request_id,
            "parent_agent_ref": self.parent_agent_ref,
            "requested_child_role": self.requested_child_role,
            "requested_reason": self.requested_reason,
            "requested_scope": self.requested_scope,
            "requested_duration": self.requested_duration,
            "requested_resources": list(self.requested_resources),
            "requested_inheritance_refs": list(self.requested_inheritance_refs),
            "forbidden_inheritance_refs": list(self.forbidden_inheritance_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "reproduction_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.authority_chain_ref:
            payload["authority_chain_ref"] = self.authority_chain_ref
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ChildBootstrapPacket:
    bootstrap_packet_id: str
    spawn_request_ref: str
    parent_agent_ref: str
    child_identity_seed_ref: str
    mission_scope: str
    allowed_memory_refs: tuple[str, ...]
    forbidden_memory_refs: tuple[str, ...]
    allowed_tool_refs: tuple[str, ...]
    forbidden_tool_refs: tuple[str, ...]
    allowed_context_refs: tuple[str, ...]
    forbidden_context_refs: tuple[str, ...]
    retention_policy_ref: str
    freshness_policy_ref: str
    redaction_policy_ref: str
    rollback_policy_ref: str
    operator_visibility_ref: str
    inherited_obligation_refs: tuple[str, ...]
    inherited_risk_refs: tuple[str, ...]
    inherited_mission_refs: tuple[str, ...]
    non_inherited_refs: tuple[str, ...]
    created_at: str
    child_agent_ref: str | None = None
    initial_autonomy_envelope_ref: str | None = None
    initial_authority_chain_ref: str | None = None
    authority_created: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ChildBootstrapPacket")
        if not self.spawn_request_ref.startswith("rib:"):
            raise RibValidationError("rib.validation.spawn_ref", "spawn_request_ref must cite rib:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-child-bootstrap-packet",
            "schema_version": RIB_SCHEMA_VERSION,
            "bootstrap_packet_id": self.bootstrap_packet_id,
            "spawn_request_ref": self.spawn_request_ref,
            "parent_agent_ref": self.parent_agent_ref,
            "child_identity_seed_ref": self.child_identity_seed_ref,
            "mission_scope": self.mission_scope,
            "allowed_memory_refs": list(self.allowed_memory_refs),
            "forbidden_memory_refs": list(self.forbidden_memory_refs),
            "allowed_tool_refs": list(self.allowed_tool_refs),
            "forbidden_tool_refs": list(self.forbidden_tool_refs),
            "allowed_context_refs": list(self.allowed_context_refs),
            "forbidden_context_refs": list(self.forbidden_context_refs),
            "retention_policy_ref": self.retention_policy_ref,
            "freshness_policy_ref": self.freshness_policy_ref,
            "redaction_policy_ref": self.redaction_policy_ref,
            "rollback_policy_ref": self.rollback_policy_ref,
            "operator_visibility_ref": self.operator_visibility_ref,
            "inherited_obligation_refs": list(self.inherited_obligation_refs),
            "inherited_risk_refs": list(self.inherited_risk_refs),
            "inherited_mission_refs": list(self.inherited_mission_refs),
            "non_inherited_refs": list(self.non_inherited_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "reproduction_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.child_agent_ref:
            payload["child_agent_ref"] = self.child_agent_ref
        if self.initial_autonomy_envelope_ref:
            payload["initial_autonomy_envelope_ref"] = self.initial_autonomy_envelope_ref
        if self.initial_authority_chain_ref:
            payload["initial_authority_chain_ref"] = self.initial_authority_chain_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class InheritanceDecision:
    inheritance_decision_id: str
    spawn_request_ref: str
    candidate_ref: str
    inheritance_type: InheritanceType
    decision: InheritanceDecisionClass
    reason: str
    evidence_refs: tuple[str, ...]
    authority_created: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="InheritanceDecision")
        _validate_no_secrets(self.inheritance_decision_id, self.candidate_ref, self.reason)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-inheritance-decision",
            "schema_version": RIB_SCHEMA_VERSION,
            "inheritance_decision_id": self.inheritance_decision_id,
            "spawn_request_ref": self.spawn_request_ref,
            "candidate_ref": self.candidate_ref,
            "inheritance_type": self.inheritance_type,
            "decision": self.decision,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
            "reproduction_is_advisory_only": True,
            "permission_granted": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ChildLifecycleReceipt:
    receipt_id: str
    spawn_request_ref: str
    lifecycle_state: LifecycleState
    state_reason: str
    evidence_refs: tuple[str, ...]
    rollback_refs: tuple[str, ...]
    created_at: str
    bootstrap_packet_ref: str | None = None
    child_agent_ref: str | None = None
    parent_notification_ref: str | None = None
    operator_review_ref: str | None = None
    authority_created: bool = False
    child_authority_created: bool = False
    external_action_taken: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="ChildLifecycleReceipt")
        if self.child_authority_created:
            raise RibValidationError(
                "rib.validation.child_authority",
                "ChildLifecycleReceipt must not set child_authority_created=true",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-child-lifecycle-receipt",
            "schema_version": RIB_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "spawn_request_ref": self.spawn_request_ref,
            "lifecycle_state": self.lifecycle_state,
            "state_reason": self.state_reason,
            "evidence_refs": list(self.evidence_refs),
            "rollback_refs": list(self.rollback_refs),
            "created_at": self.created_at,
            "authority_created": False,
            "child_authority_created": False,
            "external_action_taken": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "reproduction_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.bootstrap_packet_ref:
            payload["bootstrap_packet_ref"] = self.bootstrap_packet_ref
        if self.child_agent_ref:
            payload["child_agent_ref"] = self.child_agent_ref
        if self.parent_notification_ref:
            payload["parent_notification_ref"] = self.parent_notification_ref
        if self.operator_review_ref:
            payload["operator_review_ref"] = self.operator_review_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "authority_created",
            "child_authority_created",
            "external_action_taken",
            "permit_minted",
            "execution_admitted",
            "oea_ter_called",
            "permission_granted",
        ):
            if payload.get(key) is not False:
                raise RibValidationError("rib.validation.negative_proof", f"{key} must be false")


@dataclass(frozen=True)
class FailedSpawnRecord:
    failed_spawn_id: str
    spawn_request_ref: str
    failure_type: FailureType
    partial_artifact_refs: tuple[str, ...]
    cleanup_required: bool
    cleanup_refs: tuple[str, ...]
    retry_policy: RetryPolicy
    evidence_refs: tuple[str, ...]
    bootstrap_packet_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-failed-spawn-record",
            "schema_version": RIB_SCHEMA_VERSION,
            "failed_spawn_id": self.failed_spawn_id,
            "spawn_request_ref": self.spawn_request_ref,
            "failure_type": self.failure_type,
            "partial_artifact_refs": list(self.partial_artifact_refs),
            "cleanup_required": self.cleanup_required,
            "cleanup_refs": list(self.cleanup_refs),
            "retry_policy": self.retry_policy,
            "evidence_refs": list(self.evidence_refs),
            "child_authority_created": False,
            "reproduction_is_advisory_only": True,
        }
        if self.bootstrap_packet_ref:
            payload["bootstrap_packet_ref"] = self.bootstrap_packet_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise RibValidationError("rib.validation.authority_created", f"{label} must not set authority_created=true")


def spawn_request_from_fixture(data: dict[str, Any]) -> SpawnRequest:
    return SpawnRequest(
        spawn_request_id=str(data["spawn_request_id"]),
        parent_agent_ref=str(data.get("parent_agent_ref", DEFAULT_PARENT_AGENT_REF)),
        requested_child_role=data.get("requested_child_role", "unknown"),  # type: ignore[arg-type]
        requested_reason=str(data.get("requested_reason", "")),
        requested_scope=str(data.get("requested_scope", "")),
        requested_duration=str(data.get("requested_duration", "bounded")),
        requested_resources=tuple(data.get("requested_resources", ())),
        requested_inheritance_refs=tuple(data.get("requested_inheritance_refs", ())),
        forbidden_inheritance_refs=tuple(data.get("forbidden_inheritance_refs", ())),
        created_at=str(data.get("created_at", FIXTURE_CLOCK)),
        operator_ref=data.get("operator_ref"),
        authority_chain_ref=data.get("authority_chain_ref"),
        expires_at=data.get("expires_at"),
    )


__all__ = [
    "ChildBootstrapPacket",
    "ChildLifecycleReceipt",
    "ChildRole",
    "DEFAULT_PARENT_AGENT_REF",
    "FailedSpawnRecord",
    "FIXTURE_CLOCK",
    "FailureType",
    "InheritanceDecision",
    "InheritanceDecisionClass",
    "InheritanceType",
    "LifecycleState",
    "RIB_SCHEMA_VERSION",
    "RetryPolicy",
    "SpawnRequest",
    "classify_spawn_claim_risk",
    "spawn_request_from_fixture",
]
