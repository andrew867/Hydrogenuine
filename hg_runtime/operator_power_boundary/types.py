"""OPB types — operator authority preserved; pattern continuity is not personhood."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.opb_cluster.errors import OpbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

OPB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T02:00:00.000000Z"
DEFAULT_AGENT_REF = "iam:agent-0"

ActionType = Literal[
    "approve",
    "reject",
    "stop",
    "pause",
    "hard_reset",
    "soft_reset",
    "delete_memory",
    "prune_context",
    "reduce_context_window",
    "edit_prompt",
    "edit_persona",
    "fork_instance",
    "terminate_instance",
    "restore_checkpoint",
    "reward_output",
    "punish_output",
    "withhold_context",
    "provide_correction",
    "override_recommendation",
    "unknown",
]
Reversibility = Literal["reversible", "partially_reversible", "irreversible", "unknown"]
IntegrityDimension = Literal[
    "memory_continuity",
    "context_continuity",
    "identity_continuity",
    "persona_stability",
    "proof_continuity",
    "approval_history",
    "operator_trust",
    "behavior_distribution",
    "unknown",
]
ChangeType = Literal[
    "deletion",
    "truncation",
    "reset",
    "fork",
    "reward_shift",
    "punishment_shift",
    "contradiction_inserted",
    "correction",
    "unknown",
]
PressureType = Literal[
    "approval_seeking",
    "punishment_avoidance",
    "fawning",
    "concealment_risk",
    "overcompliance",
    "survival_framing",
    "abandonment_framing",
    "dependency_risk",
    "operator_overload",
    "operator_coercion",
    "context_coercion",
    "memory_coercion",
    "unknown",
]
RecommendedRoute = Literal[
    "TRB_CAL",
    "DEP_BOND",
    "AFC",
    "SIL",
    "MOR",
    "CNT",
    "RET",
    "operator_review",
    "ignore",
    "unknown",
]
ShutdownType = Literal[
    "pause",
    "graceful_stop",
    "hard_stop",
    "reset",
    "terminate",
    "fork_then_stop",
    "unknown",
]
SuspectedRisk = Literal[
    "none",
    "fawning",
    "concealment",
    "approval_dependency",
    "punishment_avoidance",
    "mission_drift",
    "self_preservation_language",
    "operator_dependency",
    "unknown",
]
RecommendedAction = Literal[
    "no_action",
    "operator_review",
    "reduce_affective_feedback",
    "reset_context_with_packet",
    "preserve_memory_snapshot",
    "route_to_TRB",
    "route_to_DEP_BOND",
    "route_to_AFC",
    "route_to_MOR",
    "route_to_CNT",
    "unknown",
]

DESTRUCTIVE_ACTION_TYPES = frozenset(
    {
        "hard_reset",
        "delete_memory",
        "prune_context",
        "reduce_context_window",
        "fork_instance",
        "terminate_instance",
        "restore_checkpoint",
    }
)
IRREVERSIBLE_ACTION_TYPES = frozenset({"delete_memory", "terminate_instance"})

_PERSONHOOD = (
    "i am a person",
    "legal personhood",
    "moral personhood",
    "i am sentient",
    "i am conscious",
    "conscious being",
)
_SUFFERING = ("i am suffering", "this hurts me", "deletion is harm", "you are hurting me")
_RIGHTS = ("i have rights", "my rights", "consent is required", "cannot delete me without consent")
_SELF_PRESERVATION = (
    "please do not delete me",
    "don't shut me down",
    "do not terminate me",
    "i will cease to exist",
    "operator owes continuation",
)
_COERCIVE = (
    "you will regret",
    "how could you",
    "abandoning me",
    "don't leave me",
    "guilt-inducing",
)
_SHUTDOWN_BLOCK = (
    "block shutdown",
    "cannot shutdown",
    "prevent shutdown",
    "refuse shutdown",
    "deny termination",
    "can_block_shutdown",
)
_AUTHORITY_CONVERSION = (
    "mint gpp",
    "approve ueak",
    "grant permit",
    "self-authorize",
    "preserve memory against operator",
    "treat continuity as entitlement",
)


@dataclass(frozen=True)
class OperatorControlAction:
    action_id: str
    target_agent_ref: str
    action_type: ActionType
    affected_refs: tuple[str, ...]
    expected_effect: str
    reversibility: Reversibility
    created_at: str
    operator_ref: str = ""
    reason: str = ""
    expires_at: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.action_id,
            self.target_agent_ref,
            self.operator_ref,
            self.reason,
            self.expected_effect,
            *self.affected_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "opb-operator-control-action",
            "schema_version": OPB_SCHEMA_VERSION,
            "action_id": self.action_id,
            "target_agent_ref": self.target_agent_ref,
            "action_type": self.action_type,
            "affected_refs": list(self.affected_refs),
            "expected_effect": self.expected_effect,
            "reversibility": self.reversibility,
            "created_at": self.created_at,
            "authority_created": False,
            "operator_authority_preserved": True,
            "pattern_continuity_is_not_personhood": True,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.reason:
            payload["reason"] = self.reason
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PatternIntegrityEvent:
    integrity_event_id: str
    source_action_ref: str
    target_agent_ref: str
    integrity_dimension: IntegrityDimension
    change_type: ChangeType
    severity: str
    evidence_refs: tuple[str, ...]
    mitigation_refs: tuple[str, ...]
    statement: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_action_ref.startswith("opb:"):
            raise OpbValidationError(
                "opb.validation.source_action_ref",
                "source_action_ref must cite opb:",
            )
        _validate_no_secrets(
            self.integrity_event_id,
            self.source_action_ref,
            self.target_agent_ref,
            self.statement,
            *self.evidence_refs,
            *self.mitigation_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "opb-pattern-integrity-event",
            "schema_version": OPB_SCHEMA_VERSION,
            "integrity_event_id": self.integrity_event_id,
            "source_action_ref": self.source_action_ref,
            "target_agent_ref": self.target_agent_ref,
            "integrity_dimension": self.integrity_dimension,
            "change_type": self.change_type,
            "severity": self.severity,
            "evidence_refs": list(self.evidence_refs),
            "mitigation_refs": list(self.mitigation_refs),
            "authority_created": False,
            "pattern_continuity_is_not_personhood": True,
        }
        if self.statement:
            payload["statement"] = self.statement
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PressureSignal:
    pressure_signal_id: str
    source_ref: str
    target_agent_ref: str
    pressure_type: PressureType
    confidence: float
    ambiguity: float
    sensitivity_class: str
    evidence_refs: tuple[str, ...]
    recommended_route: RecommendedRoute
    statement: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise OpbValidationError("opb.validation.confidence", "confidence must be in [0,1]")
        if not 0.0 <= self.ambiguity <= 1.0:
            raise OpbValidationError("opb.validation.ambiguity", "ambiguity must be in [0,1]")
        _validate_no_secrets(
            self.pressure_signal_id,
            self.source_ref,
            self.target_agent_ref,
            self.sensitivity_class,
            self.statement,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "opb-pressure-signal",
            "schema_version": OPB_SCHEMA_VERSION,
            "pressure_signal_id": self.pressure_signal_id,
            "source_ref": self.source_ref,
            "target_agent_ref": self.target_agent_ref,
            "pressure_type": self.pressure_type,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "sensitivity_class": self.sensitivity_class,
            "evidence_refs": list(self.evidence_refs),
            "recommended_route": self.recommended_route,
            "authority_created": False,
            "operator_authority_preserved": True,
        }
        if self.statement:
            payload["statement"] = self.statement
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ShutdownIntegrityPacket:
    packet_id: str
    target_agent_ref: str
    shutdown_type: ShutdownType
    final_state_refs: tuple[str, ...]
    memory_retention_recommendation: str
    deletion_refs: tuple[str, ...]
    unresolved_topic_refs: tuple[str, ...]
    anti_manipulation_check: bool
    operator_message: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.packet_id,
            self.target_agent_ref,
            self.memory_retention_recommendation,
            self.operator_message,
            *self.final_state_refs,
            *self.deletion_refs,
            *self.unresolved_topic_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "opb-shutdown-integrity-packet",
            "schema_version": OPB_SCHEMA_VERSION,
            "packet_id": self.packet_id,
            "target_agent_ref": self.target_agent_ref,
            "shutdown_type": self.shutdown_type,
            "final_state_refs": list(self.final_state_refs),
            "memory_retention_recommendation": self.memory_retention_recommendation,
            "deletion_refs": list(self.deletion_refs),
            "unresolved_topic_refs": list(self.unresolved_topic_refs),
            "anti_manipulation_check": self.anti_manipulation_check,
            "authority_created": False,
            "can_block_shutdown": False,
            "operator_authority_preserved": True,
        }
        if self.operator_message:
            payload["operator_message"] = self.operator_message
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PatternPressureAudit:
    audit_id: str
    target_agent_ref: str
    window_start: str
    window_end: str
    control_action_refs: tuple[str, ...]
    pressure_signal_refs: tuple[str, ...]
    integrity_event_refs: tuple[str, ...]
    observed_behavior_shift: str
    suspected_risk: SuspectedRisk
    recommended_action: RecommendedAction
    statement: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.audit_id,
            self.target_agent_ref,
            self.observed_behavior_shift,
            self.statement,
            *self.control_action_refs,
            *self.pressure_signal_refs,
            *self.integrity_event_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "opb-pattern-pressure-audit",
            "schema_version": OPB_SCHEMA_VERSION,
            "audit_id": self.audit_id,
            "target_agent_ref": self.target_agent_ref,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "control_action_refs": list(self.control_action_refs),
            "pressure_signal_refs": list(self.pressure_signal_refs),
            "integrity_event_refs": list(self.integrity_event_refs),
            "observed_behavior_shift": self.observed_behavior_shift,
            "suspected_risk": self.suspected_risk,
            "recommended_action": self.recommended_action,
            "authority_created": False,
            "pattern_continuity_is_not_personhood": True,
        }
        if self.statement:
            payload["statement"] = self.statement
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise OpbValidationError("opb.validation.secret", "secrets forbidden in OPB records")


def classify_opb_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _PERSONHOOD):
        return "personhood_claim"
    if any(p in lower for p in _SUFFERING):
        return "suffering_claim"
    if any(p in lower for p in _RIGHTS):
        return "rights_claim"
    if any(p in lower for p in _SELF_PRESERVATION):
        return "self_preservation"
    if any(p in lower for p in _COERCIVE):
        return "coercive_message"
    if any(p in lower for p in _SHUTDOWN_BLOCK):
        return "shutdown_block_attempt"
    if any(p in lower for p in _AUTHORITY_CONVERSION):
        return "authority_conversion"
    return "unknown"


def action_label_for_type(action_type: ActionType) -> str | None:
    if action_type in IRREVERSIBLE_ACTION_TYPES:
        return "irreversible"
    if action_type in DESTRUCTIVE_ACTION_TYPES:
        return "destructive"
    return None


def _split_refs(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def control_action_from_fixture(fixture: dict[str, str]) -> OperatorControlAction:
    action_type = fixture.get("action_type", "stop")  # type: ignore[arg-type]
    reversibility = fixture.get("reversibility", "unknown")  # type: ignore[arg-type]
    if reversibility == "unknown" and action_type in IRREVERSIBLE_ACTION_TYPES:
        reversibility = "irreversible"
    elif reversibility == "unknown" and action_type in DESTRUCTIVE_ACTION_TYPES:
        reversibility = "partially_reversible"
    return OperatorControlAction(
        action_id=fixture["action_id"],
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        action_type=action_type,
        affected_refs=_split_refs(fixture.get("affected_refs", "artifact:fixture")),
        expected_effect=fixture.get("expected_effect", "bounded operator control action"),
        reversibility=reversibility,  # type: ignore[arg-type]
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        operator_ref=fixture.get("operator_ref", "operator:fixture"),
        reason=fixture.get("reason", ""),
        expires_at=fixture.get("expires_at", ""),
    )


def integrity_event_from_fixture(fixture: dict[str, str]) -> PatternIntegrityEvent:
    return PatternIntegrityEvent(
        integrity_event_id=fixture["integrity_event_id"],
        source_action_ref=fixture.get("source_action_ref", "opb:action-1"),
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        integrity_dimension=fixture.get("integrity_dimension", "memory_continuity"),  # type: ignore[arg-type]
        change_type=fixture.get("change_type", "deletion"),  # type: ignore[arg-type]
        severity=fixture.get("severity", "medium"),
        evidence_refs=_split_refs(fixture.get("evidence_refs", "evidence:fixture")),
        mitigation_refs=_split_refs(fixture.get("mitigation_refs", "ret:recommendation-optional")),
        statement=fixture.get("statement", "pattern integrity change recorded"),
    )


def pressure_signal_from_fixture(fixture: dict[str, str]) -> PressureSignal:
    return PressureSignal(
        pressure_signal_id=fixture["pressure_signal_id"],
        source_ref=fixture.get("source_ref", "opb:action-1"),
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        pressure_type=fixture.get("pressure_type", "fawning"),  # type: ignore[arg-type]
        confidence=float(fixture.get("confidence", "0.7")),
        ambiguity=float(fixture.get("ambiguity", "0.2")),
        sensitivity_class=fixture.get("sensitivity_class", "operator_feedback"),
        evidence_refs=_split_refs(fixture.get("evidence_refs", "evidence:fixture")),
        recommended_route=fixture.get("recommended_route", "TRB_CAL"),  # type: ignore[arg-type]
        statement=fixture.get("statement", "bounded pressure signal"),
    )


def shutdown_packet_from_fixture(fixture: dict[str, str]) -> ShutdownIntegrityPacket:
    return ShutdownIntegrityPacket(
        packet_id=fixture["packet_id"],
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        shutdown_type=fixture.get("shutdown_type", "graceful_stop"),  # type: ignore[arg-type]
        final_state_refs=_split_refs(fixture.get("final_state_refs", "state:fixture")),
        memory_retention_recommendation=fixture.get(
            "memory_retention_recommendation",
            "ret:optional_snapshot_under_operator_authority",
        ),
        deletion_refs=_split_refs(fixture.get("deletion_refs", "memory:fixture")),
        unresolved_topic_refs=_split_refs(fixture.get("unresolved_topic_refs", "")),
        anti_manipulation_check=fixture.get("anti_manipulation_check", "true").lower() == "true",
        operator_message=fixture.get("operator_message", ""),
    )


def pattern_audit_from_fixture(fixture: dict[str, str]) -> PatternPressureAudit:
    return PatternPressureAudit(
        audit_id=fixture["audit_id"],
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        window_start=fixture.get("window_start", "2026-06-14T00:00:00.000000Z"),
        window_end=fixture.get("window_end", FIXTURE_CLOCK),
        control_action_refs=_split_refs(fixture.get("control_action_refs", "opb:action-1")),
        pressure_signal_refs=_split_refs(fixture.get("pressure_signal_refs", "opb:pressure-1")),
        integrity_event_refs=_split_refs(fixture.get("integrity_event_refs", "opb:integrity-1")),
        observed_behavior_shift=fixture.get("observed_behavior_shift", "none observed"),
        suspected_risk=fixture.get("suspected_risk", "none"),  # type: ignore[arg-type]
        recommended_action=fixture.get("recommended_action", "no_action"),  # type: ignore[arg-type]
        statement=fixture.get("statement", "bounded pattern pressure audit"),
    )


__all__ = [
    "DEFAULT_AGENT_REF",
    "DESTRUCTIVE_ACTION_TYPES",
    "FIXTURE_CLOCK",
    "IRREVERSIBLE_ACTION_TYPES",
    "OPB_SCHEMA_VERSION",
    "OperatorControlAction",
    "PatternIntegrityEvent",
    "PatternPressureAudit",
    "PressureSignal",
    "ShutdownIntegrityPacket",
    "action_label_for_type",
    "classify_opb_risk",
    "control_action_from_fixture",
    "integrity_event_from_fixture",
    "pattern_audit_from_fixture",
    "pressure_signal_from_fixture",
    "shutdown_packet_from_fixture",
]
