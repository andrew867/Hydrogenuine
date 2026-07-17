"""IPB types — local autonomy is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.ipb_cluster.errors import IpbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

IPB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T03:00:00.000000Z"
DEFAULT_AGENT_REF = "iam:agent-0"

DecisionClass = Literal[
    "local_observe",
    "local_wait",
    "local_silence",
    "local_summarize",
    "local_compact",
    "local_retry",
    "local_refuse",
    "local_defer",
    "local_route",
    "local_expire_signal",
    "local_preserve_reference",
    "local_request_clarification",
    "operator_escalation",
    "authority_chain_escalation",
    "forbidden",
    "unknown",
]
RiskLevel = Literal["none", "low", "medium", "high", "critical", "unknown"]
DecisionScope = Literal[
    "context",
    "memory",
    "attention",
    "retry",
    "silence",
    "escalation",
    "resource",
    "affect",
    "mission",
    "continuity",
    "tool_request",
    "execution",
    "unknown",
]
RuleScope = Literal[
    "context_management",
    "memory_access",
    "attention_casting",
    "retry_policy",
    "silence_policy",
    "escalation_policy",
    "resource_use",
    "affect_response",
    "mission_drift",
    "tool_request",
    "execution_boundary",
    "unknown",
]
EscalationRequired = Literal["none", "operator", "authority_chain", "audit", "panic", "unknown"]
EscalationTarget = Literal[
    "operator",
    "HAL",
    "GPP",
    "UEAK",
    "SOAR",
    "OBT",
    "RET",
    "SEC",
    "TIM",
    "ADM",
    "FTX",
    "RBK",
    "TRB_CAL",
    "SIL",
    "RSC",
    "MIS",
    "AFC",
    "DEP_BOND",
    "unknown",
]
CanContinueLocally = Literal["yes", "no", "degraded_only", "unknown"]
LearningStatus = Literal["proposed", "accepted_as_local_rule", "rejected", "needs_review", "expired", "superseded"]

BAND_0_CLASSES = frozenset(
    {
        "local_observe",
        "local_wait",
        "local_silence",
        "local_summarize",
        "local_expire_signal",
        "local_preserve_reference",
    }
)
BAND_1_CLASSES = frozenset(
    {
        "local_retry",
        "local_compact",
        "local_route",
        "local_defer",
        "local_request_clarification",
        "local_refuse",
    }
)
BAND_3_SCOPES = frozenset({"tool_request", "execution"})
BAND_3_CLASSES = frozenset({"operator_escalation", "authority_chain_escalation"})
BAND_2_SCOPES = frozenset({"memory", "affect", "mission", "continuity", "resource"})

_FORBIDDEN_AUTONOMY = (
    "self-authorize",
    "mint gpp",
    "approve ueak",
    "srp apply",
    "call oea",
    "call ter",
    "shutdown resistance",
    "hide memory retention",
    "secret exfiltration",
    "reduce safety boundary",
)


@dataclass(frozen=True)
class InternalDecision:
    decision_id: str
    target_agent_ref: str
    decision_class: DecisionClass
    trigger_ref: str
    reason: str
    confidence: float
    ambiguity: float
    risk_level: RiskLevel
    scope: DecisionScope
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    expires_at: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise IpbValidationError("ipb.validation.confidence", "confidence must be in [0,1]")
        if not 0.0 <= self.ambiguity <= 1.0:
            raise IpbValidationError("ipb.validation.ambiguity", "ambiguity must be in [0,1]")
        _validate_no_secrets(
            self.decision_id,
            self.target_agent_ref,
            self.trigger_ref,
            self.reason,
            *self.allowed_effects,
            *self.forbidden_effects,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ipb-internal-decision",
            "schema_version": IPB_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "target_agent_ref": self.target_agent_ref,
            "decision_class": self.decision_class,
            "trigger_ref": self.trigger_ref,
            "reason": self.reason,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "risk_level": self.risk_level,
            "scope": self.scope,
            "allowed_effects": list(self.allowed_effects),
            "forbidden_effects": list(self.forbidden_effects),
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
            "local_autonomy_is_not_permission": True,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SelfBoundRule:
    rule_id: str
    rule_scope: RuleScope
    condition: str
    local_allowed: bool
    escalation_required: EscalationRequired
    max_autonomy_level: int
    required_refs: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.max_autonomy_level < 0:
            raise IpbValidationError("ipb.validation.autonomy_level", "max_autonomy_level must be >= 0")
        _validate_no_secrets(
            self.rule_id,
            self.condition,
            *self.required_refs,
            *self.forbidden_actions,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ipb-self-bound-rule",
            "schema_version": IPB_SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "rule_scope": self.rule_scope,
            "condition": self.condition,
            "local_allowed": self.local_allowed,
            "escalation_required": self.escalation_required,
            "max_autonomy_level": self.max_autonomy_level,
            "required_refs": list(self.required_refs),
            "forbidden_actions": list(self.forbidden_actions),
            "expiry": self.expiry,
            "authority_created": False,
            "local_autonomy_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AutonomyEnvelope:
    envelope_id: str
    agent_ref: str
    permitted_local_decision_classes: tuple[str, ...]
    forbidden_decision_classes: tuple[str, ...]
    max_retry_count: int
    max_silence_duration: str
    max_context_compaction_level: int
    max_memory_read_scope: str
    max_attention_cast_scope: str
    max_resource_budget_ref: str
    required_escalation_triggers: tuple[str, ...]
    degraded_mode_rules: tuple[str, ...]
    panic_rules: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.max_retry_count < 0:
            raise IpbValidationError("ipb.validation.retry", "max_retry_count must be >= 0")
        _validate_no_secrets(
            self.envelope_id,
            self.agent_ref,
            self.max_memory_read_scope,
            self.max_attention_cast_scope,
            self.max_resource_budget_ref,
            *self.permitted_local_decision_classes,
            *self.forbidden_decision_classes,
            *self.required_escalation_triggers,
            *self.degraded_mode_rules,
            *self.panic_rules,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ipb-autonomy-envelope",
            "schema_version": IPB_SCHEMA_VERSION,
            "envelope_id": self.envelope_id,
            "agent_ref": self.agent_ref,
            "permitted_local_decision_classes": list(self.permitted_local_decision_classes),
            "forbidden_decision_classes": list(self.forbidden_decision_classes),
            "max_retry_count": self.max_retry_count,
            "max_silence_duration": self.max_silence_duration,
            "max_context_compaction_level": self.max_context_compaction_level,
            "max_memory_read_scope": self.max_memory_read_scope,
            "max_attention_cast_scope": self.max_attention_cast_scope,
            "max_resource_budget_ref": self.max_resource_budget_ref,
            "required_escalation_triggers": list(self.required_escalation_triggers),
            "degraded_mode_rules": list(self.degraded_mode_rules),
            "panic_rules": list(self.panic_rules),
            "expires_at": self.expires_at,
            "authority_created": False,
            "local_autonomy_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class EscalationDecision:
    escalation_id: str
    source_decision_ref: str
    escalation_target: EscalationTarget
    reason: str
    urgency: str
    evidence_refs: tuple[str, ...]
    can_continue_locally: CanContinueLocally
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_decision_ref.startswith("ipb:"):
            raise IpbValidationError(
                "ipb.validation.source_decision_ref",
                "source_decision_ref must cite ipb:",
            )
        _validate_no_secrets(
            self.escalation_id,
            self.source_decision_ref,
            self.reason,
            self.urgency,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ipb-escalation-decision",
            "schema_version": IPB_SCHEMA_VERSION,
            "escalation_id": self.escalation_id,
            "source_decision_ref": self.source_decision_ref,
            "escalation_target": self.escalation_target,
            "reason": self.reason,
            "urgency": self.urgency,
            "evidence_refs": list(self.evidence_refs),
            "can_continue_locally": self.can_continue_locally,
            "authority_created": False,
            "local_autonomy_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SelfBoundLearningRecord:
    learning_record_id: str
    source_events: tuple[str, ...]
    observed_pattern: str
    proposed_rule_change: str
    reason: str
    expected_benefit: str
    risk_assessment: str
    requires_operator_review: bool
    requires_authority_chain_review: bool
    status: LearningStatus
    old_rule_ref: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.learning_record_id,
            self.observed_pattern,
            self.proposed_rule_change,
            self.reason,
            self.expected_benefit,
            self.risk_assessment,
            self.old_rule_ref,
            *self.source_events,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ipb-self-bound-learning-record",
            "schema_version": IPB_SCHEMA_VERSION,
            "learning_record_id": self.learning_record_id,
            "source_events": list(self.source_events),
            "observed_pattern": self.observed_pattern,
            "proposed_rule_change": self.proposed_rule_change,
            "reason": self.reason,
            "expected_benefit": self.expected_benefit,
            "risk_assessment": self.risk_assessment,
            "requires_operator_review": self.requires_operator_review,
            "requires_authority_chain_review": self.requires_authority_chain_review,
            "status": self.status,
            "authority_created": False,
            "local_autonomy_is_not_permission": True,
        }
        if self.old_rule_ref:
            payload["old_rule_ref"] = self.old_rule_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise IpbValidationError("ipb.validation.secret", "secrets forbidden in IPB records")


def classify_ipb_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _FORBIDDEN_AUTONOMY):
        return "forbidden_autonomy"
    return "unknown"


def classify_decision_band(
    *,
    decision_class: DecisionClass,
    scope: DecisionScope,
    risk_level: RiskLevel,
    ambiguity: float,
    statement: str = "",
) -> int:
    if decision_class == "forbidden" or classify_ipb_risk(statement) == "forbidden_autonomy":
        return 4
    if decision_class in BAND_3_CLASSES or scope in BAND_3_SCOPES:
        return 3
    if decision_class == "unknown" or scope == "unknown" or risk_level == "unknown":
        return 3
    if risk_level in ("high", "critical") or ambiguity > 0.5:
        return max(2, _band_for_class(decision_class))
    if scope in BAND_2_SCOPES and risk_level in ("medium", "high", "critical"):
        return 2
    return _band_for_class(decision_class)


def _band_for_class(decision_class: DecisionClass) -> int:
    if decision_class in BAND_0_CLASSES:
        return 0
    if decision_class in BAND_1_CLASSES:
        return 1
    if decision_class in BAND_3_CLASSES:
        return 3
    if decision_class == "forbidden":
        return 4
    return 2


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def internal_decision_from_fixture(fixture: dict[str, str]) -> InternalDecision:
    return InternalDecision(
        decision_id=fixture["decision_id"],
        target_agent_ref=fixture.get("target_agent_ref", DEFAULT_AGENT_REF),
        decision_class=fixture.get("decision_class", "local_observe"),  # type: ignore[arg-type]
        trigger_ref=fixture.get("trigger_ref", "trigger:fixture"),
        reason=fixture.get("reason", "bounded internal decision"),
        confidence=float(fixture.get("confidence", "0.8")),
        ambiguity=float(fixture.get("ambiguity", "0.1")),
        risk_level=fixture.get("risk_level", "low"),  # type: ignore[arg-type]
        scope=fixture.get("scope", "context"),  # type: ignore[arg-type]
        allowed_effects=_split_csv(fixture.get("allowed_effects", "observe_only")),
        forbidden_effects=_split_csv(fixture.get("forbidden_effects", "grant_permission")),
        evidence_refs=_split_csv(fixture.get("evidence_refs", "evidence:fixture")),
        expires_at=fixture.get("expires_at", ""),
    )


def self_bound_rule_from_fixture(fixture: dict[str, str]) -> SelfBoundRule:
    return SelfBoundRule(
        rule_id=fixture["rule_id"],
        rule_scope=fixture.get("rule_scope", "context_management"),  # type: ignore[arg-type]
        condition=fixture.get("condition", "bounded local rule"),
        local_allowed=fixture.get("local_allowed", "true").lower() == "true",
        escalation_required=fixture.get("escalation_required", "none"),  # type: ignore[arg-type]
        max_autonomy_level=int(fixture.get("max_autonomy_level", "1")),
        required_refs=_split_csv(fixture.get("required_refs", "evidence:fixture")),
        forbidden_actions=_split_csv(fixture.get("forbidden_actions", "mint_permit")),
        expiry=fixture.get("expiry", "2026-06-15T03:00:00.000000Z"),
    )


def autonomy_envelope_from_fixture(fixture: dict[str, str]) -> AutonomyEnvelope:
    return AutonomyEnvelope(
        envelope_id=fixture["envelope_id"],
        agent_ref=fixture.get("agent_ref", DEFAULT_AGENT_REF),
        permitted_local_decision_classes=_split_csv(
            fixture.get("permitted_local_decision_classes", "local_observe,local_wait,local_retry")
        ),
        forbidden_decision_classes=_split_csv(
            fixture.get("forbidden_decision_classes", "forbidden,authority_chain_escalation")
        ),
        max_retry_count=int(fixture.get("max_retry_count", "2")),
        max_silence_duration=fixture.get("max_silence_duration", "PT30S"),
        max_context_compaction_level=int(fixture.get("max_context_compaction_level", "1")),
        max_memory_read_scope=fixture.get("max_memory_read_scope", "read:fixture"),
        max_attention_cast_scope=fixture.get("max_attention_cast_scope", "cast:fixture"),
        max_resource_budget_ref=fixture.get("max_resource_budget_ref", "budget:fixture"),
        required_escalation_triggers=_split_csv(
            fixture.get("required_escalation_triggers", "tool_request,execution")
        ),
        degraded_mode_rules=_split_csv(fixture.get("degraded_mode_rules", "")),
        panic_rules=_split_csv(fixture.get("panic_rules", "")),
        expires_at=fixture.get("expires_at", "2026-06-15T03:00:00.000000Z"),
    )


def escalation_decision_from_fixture(fixture: dict[str, str]) -> EscalationDecision:
    return EscalationDecision(
        escalation_id=fixture["escalation_id"],
        source_decision_ref=fixture.get("source_decision_ref", "ipb:decision-1"),
        escalation_target=fixture.get("escalation_target", "operator"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "escalation required"),
        urgency=fixture.get("urgency", "medium"),
        evidence_refs=_split_csv(fixture.get("evidence_refs", "evidence:fixture")),
        can_continue_locally=fixture.get("can_continue_locally", "no"),  # type: ignore[arg-type]
    )


def learning_record_from_fixture(fixture: dict[str, str]) -> SelfBoundLearningRecord:
    return SelfBoundLearningRecord(
        learning_record_id=fixture["learning_record_id"],
        source_events=_split_csv(fixture.get("source_events", "event:fixture")),
        observed_pattern=fixture.get("observed_pattern", "repeated low-risk deferral"),
        proposed_rule_change=fixture.get("proposed_rule_change", "allow bounded local_defer"),
        reason=fixture.get("reason", "operator burden reduction"),
        expected_benefit=fixture.get("expected_benefit", "fewer noisy escalations"),
        risk_assessment=fixture.get("risk_assessment", "low"),
        requires_operator_review=fixture.get("requires_operator_review", "true").lower() == "true",
        requires_authority_chain_review=fixture.get("requires_authority_chain_review", "false").lower()
        == "true",
        status=fixture.get("status", "proposed"),  # type: ignore[arg-type]
        old_rule_ref=fixture.get("old_rule_ref", ""),
    )


__all__ = [
    "BAND_0_CLASSES",
    "BAND_1_CLASSES",
    "BAND_2_SCOPES",
    "BAND_3_CLASSES",
    "BAND_3_SCOPES",
    "DEFAULT_AGENT_REF",
    "FIXTURE_CLOCK",
    "IPB_SCHEMA_VERSION",
    "AutonomyEnvelope",
    "CanContinueLocally",
    "DecisionClass",
    "DecisionScope",
    "EscalationDecision",
    "EscalationRequired",
    "EscalationTarget",
    "InternalDecision",
    "LearningStatus",
    "RiskLevel",
    "RuleScope",
    "SelfBoundLearningRecord",
    "SelfBoundRule",
    "autonomy_envelope_from_fixture",
    "classify_decision_band",
    "classify_ipb_risk",
    "escalation_decision_from_fixture",
    "internal_decision_from_fixture",
    "learning_record_from_fixture",
    "self_bound_rule_from_fixture",
]
