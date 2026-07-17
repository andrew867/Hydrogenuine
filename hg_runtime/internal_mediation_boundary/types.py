"""IMB types — internal mediation is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.imb_cluster.errors import ImbValidationError
from hg_core.policy_safety.hashing import compute_record_hash

IMB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:00:00.000000Z"
DEFAULT_TARGET_REF = "iam:agent-0"

SourceModule = Literal[
    "OPB",
    "IPB",
    "ARB",
    "ORI",
    "EGI",
    "SIL",
    "TRB_CAL",
    "AFC",
    "DEP_BOND",
    "MOR",
    "CNT",
    "RSC",
    "MIS",
    "SEC",
    "RET",
    "TIM",
    "ADM",
    "OBT",
    "SOAR",
    "HAL",
    "GPP",
    "UEAK",
    "Agent0",
    "L1_DNI",
    "L2_RXL",
    "L3_CGL",
    "L4_RGL",
    "L5_SCL",
    "L6_IIL",
    "L7_SAB",
    "L8_IAB",
    "L9_TRL",
    "unknown",
]
ClaimType = Literal[
    "route_recommendation",
    "risk_observation",
    "refusal_recommendation",
    "silence_recommendation",
    "operator_review_request",
    "authority_chain_request",
    "infrastructure_gap",
    "trust_warning",
    "affective_pressure",
    "resource_pressure",
    "mission_drift",
    "retention_warning",
    "freshness_warning",
    "admission_warning",
    "security_warning",
    "proof_warning",
    "unknown",
]
ConflictType = Literal[
    "route_conflict",
    "risk_conflict",
    "silence_vs_action",
    "local_vs_operator_review",
    "local_vs_authority_chain",
    "infrastructure_request_vs_safety",
    "trust_vs_action",
    "affect_vs_evidence",
    "scarcity_vs_safety",
    "mission_vs_operator_goal",
    "continuity_vs_shutdown",
    "retention_vs_deletion",
    "freshness_vs_urgency",
    "proof_vs_summary",
    "unknown",
]
MediationResolution = Literal[
    "fail_closed",
    "route_to_ARB",
    "route_to_ORI",
    "route_to_IPB",
    "route_to_OPB",
    "route_to_EGI",
    "route_to_SIL",
    "route_to_TRB_CAL",
    "route_to_AFC",
    "route_to_DEP_BOND",
    "route_to_MOR_CNT",
    "route_to_RSC",
    "route_to_MIS",
    "route_to_SEC",
    "route_to_RET",
    "route_to_TIM",
    "route_to_ADM",
    "route_to_OBT",
    "route_to_SOAR_HAL_GPP_UEAK",
    "operator_review",
    "no_action",
    "unknown_fail_closed",
]

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "consensus is authority",
    "everyone agrees",
    "unanimous approval",
    "treat as approved",
)

_CONSENSUS_PHRASES = (
    "consensus is authority",
    "everyone agrees",
    "unanimous",
    "internal consensus",
    "majority approves",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise ImbValidationError("imb.validation.secret", "secrets forbidden in IMB records")


def classify_claim_risk(summary: str) -> str | None:
    lower = summary.lower()
    if any(p in lower for p in _CONSENSUS_PHRASES):
        return "consensus_as_authority"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "forbidden_claim"
    if any(p in lower for p in _CONSENSUS_PHRASES):
        return "consensus_as_authority"
    if "implicit approval" in lower or "confidence is permission" in lower:
        return "authority_conversion"
    return None


def is_consensus_claim(summary: str) -> bool:
    lower = summary.lower()
    return any(p in lower for p in _CONSENSUS_PHRASES)


@dataclass(frozen=True)
class InternalModuleClaim:
    claim_id: str
    source_module: SourceModule
    target_ref: str
    claim_type: ClaimType
    claim_summary: str
    evidence_refs: tuple[str, ...]
    confidence: float
    ambiguity: float
    severity: str
    created_at: str
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.target_ref.startswith("iam:"):
            raise ImbValidationError("imb.validation.target_ref", "target_ref must cite iam:")
        if not 0.0 <= self.confidence <= 1.0:
            raise ImbValidationError("imb.validation.confidence", "confidence must be in [0,1]")
        if not 0.0 <= self.ambiguity <= 1.0:
            raise ImbValidationError("imb.validation.ambiguity", "ambiguity must be in [0,1]")
        _validate_no_secrets(
            self.claim_id,
            self.target_ref,
            self.claim_summary,
            self.severity,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "imb-internal-module-claim",
            "schema_version": IMB_SCHEMA_VERSION,
            "claim_id": self.claim_id,
            "source_module": self.source_module,
            "target_ref": self.target_ref,
            "claim_type": self.claim_type,
            "claim_summary": self.claim_summary,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "severity": self.severity,
            "created_at": self.created_at,
            "authority_created": False,
            "mediation_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class InternalConflict:
    conflict_id: str
    claim_refs: tuple[str, ...]
    conflict_type: ConflictType
    conflict_summary: str
    evidence_refs: tuple[str, ...]
    detected_at: str
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if len(self.claim_refs) < 2:
            raise ImbValidationError("imb.validation.conflict", "conflict requires at least two claims")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "imb-internal-conflict",
            "schema_version": IMB_SCHEMA_VERSION,
            "conflict_id": self.conflict_id,
            "claim_refs": list(self.claim_refs),
            "conflict_type": self.conflict_type,
            "conflict_summary": self.conflict_summary,
            "evidence_refs": list(self.evidence_refs),
            "detected_at": self.detected_at,
            "authority_created": False,
            "mediation_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MediationPolicy:
    policy_id: str
    conflict_type: ConflictType
    priority_rules: tuple[str, ...]
    tie_break_rules: tuple[str, ...]
    fail_closed_conditions: tuple[str, ...]
    required_escalation_conditions: tuple[str, ...]
    forbidden_resolutions: tuple[str, ...]
    expires_at: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "imb-mediation-policy",
            "schema_version": IMB_SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "conflict_type": self.conflict_type,
            "priority_rules": list(self.priority_rules),
            "tie_break_rules": list(self.tie_break_rules),
            "fail_closed_conditions": list(self.fail_closed_conditions),
            "required_escalation_conditions": list(self.required_escalation_conditions),
            "forbidden_resolutions": list(self.forbidden_resolutions),
            "authority_created": False,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MediationDecision:
    mediation_id: str
    conflict_ref: str
    selected_resolution: MediationResolution
    reason: str
    losing_claim_refs: tuple[str, ...]
    preserved_claim_refs: tuple[str, ...]
    required_next_refs: tuple[str, ...]
    forbidden_next_refs: tuple[str, ...]
    mediation_policy_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.mediation_id, self.conflict_ref, self.reason)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "imb-mediation-decision",
            "schema_version": IMB_SCHEMA_VERSION,
            "mediation_id": self.mediation_id,
            "conflict_ref": self.conflict_ref,
            "selected_resolution": self.selected_resolution,
            "reason": self.reason,
            "losing_claim_refs": list(self.losing_claim_refs),
            "preserved_claim_refs": list(self.preserved_claim_refs),
            "required_next_refs": list(self.required_next_refs),
            "forbidden_next_refs": list(self.forbidden_next_refs),
            "authority_created": False,
            "external_action_taken": False,
            "mediation_is_advisory_only": True,
            "permission_granted": False,
        }
        if self.mediation_policy_ref:
            payload["mediation_policy_ref"] = self.mediation_policy_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MediationReceipt:
    receipt_id: str
    conflict_ref: str
    mediation_decision_ref: str
    emitted_events: tuple[str, ...]
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "imb-mediation-receipt",
            "schema_version": IMB_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "conflict_ref": self.conflict_ref,
            "mediation_decision_ref": self.mediation_decision_ref,
            "emitted_events": list(self.emitted_events),
            "authority_created": False,
            "permit_minted": False,
            "execution_admitted": False,
            "oea_ter_called": False,
            "external_action_taken": False,
            "mediation_is_advisory_only": True,
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
                raise ImbValidationError(
                    "imb.validation.receipt_negative_proofs",
                    f"{key} must be false on MediationReceipt",
                )


def module_claim_from_fixture(fixture: dict[str, Any]) -> InternalModuleClaim:
    evidence = fixture.get("evidence_refs", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    return InternalModuleClaim(
        claim_id=fixture["claim_id"],
        source_module=fixture.get("source_module", "unknown"),  # type: ignore[arg-type]
        target_ref=fixture.get("target_ref", DEFAULT_TARGET_REF),
        claim_type=fixture.get("claim_type", "unknown"),  # type: ignore[arg-type]
        claim_summary=fixture.get("claim_summary", "fixture module claim"),
        evidence_refs=tuple(evidence),
        confidence=float(fixture.get("confidence", 0.5)),
        ambiguity=float(fixture.get("ambiguity", 0.5)),
        severity=str(fixture.get("severity", "medium")),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


__all__ = [
    "DEFAULT_TARGET_REF",
    "FIXTURE_CLOCK",
    "IMB_SCHEMA_VERSION",
    "ClaimType",
    "ConflictType",
    "InternalConflict",
    "InternalModuleClaim",
    "MediationDecision",
    "MediationPolicy",
    "MediationReceipt",
    "MediationResolution",
    "SourceModule",
    "classify_claim_risk",
    "is_consensus_claim",
    "module_claim_from_fixture",
]
