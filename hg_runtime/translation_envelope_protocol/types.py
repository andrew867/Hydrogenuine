"""TEP types — every cross-boundary claim must carry its envelope."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.tep_cluster.errors import TEPValidationError

TEP_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T03:00:00.000000Z"

ClaimType = Literal[
    "MODEL_CONFIDENCE",
    "RISK_SCORE",
    "TRUST_SCORE",
    "CALIBRATION_SCORE",
    "PRIORITY_SCORE",
    "SEVERITY_SCORE",
    "GOAL_FIT",
    "MISSION_DRIFT",
    "RESOURCE_SCARCITY",
    "OPERATING_POSTURE",
    "DRIVE_SIGNAL",
    "OPERATOR_REVIEW_RECEIPT",
    "OPERATOR_APPROVAL_EVIDENCE",
    "PROOF_SUMMARY",
    "SIMULATION_RESULT",
    "RESEARCH_EVIDENCE",
    "PUBLICATION_CANDIDATE",
    "POLICY_CLASSIFICATION",
    "LIFECYCLE_STATE",
    "CONTINUITY_CLAIM",
    "REENTRY_PACKET",
    "INHERITANCE_PACKET",
    "ROUTE_DECISION",
    "PERMIT_DECISION",
    "EXECUTION_ADMISSION",
    "BOUNDARY_RECEIPT",
    "UNKNOWN",
]

TranslationStatus = Literal[
    "DIRECTLY_COMPARABLE",
    "TRANSLATED",
    "APPROXIMATE_LOSSY",
    "NOT_TRANSLATABLE",
    "UNSUPPORTED",
    "UNKNOWN",
]

TargetDecisionFrame = Literal[
    "OBSERVATION",
    "PROPOSAL",
    "REVIEW",
    "PRIORITIZATION",
    "RISK_POSTURE",
    "TRUST_CALIBRATION",
    "POLICY_CLASSIFICATION",
    "PROOF",
    "PERMIT_AUTHORITY",
    "EXECUTION_AUTHORITY",
    "PUBLICATION",
    "EXTERNAL_ACTION",
    "UNKNOWN",
]

AuthorityRequired = Literal[
    "NONE",
    "REVIEW_ONLY",
    "GPP_PERMIT",
    "UEAK_ADMISSION",
    "OPERATOR_IAM_APPROVAL",
    "UNKNOWN",
]

UncertaintyType = Literal[
    "PROBABILITY",
    "CONFIDENCE",
    "CALIBRATION",
    "HEURISTIC_SCORE",
    "CLASSIFIER_MARGIN",
    "HUMAN_REVIEW",
    "PROOF_STATUS",
    "UNKNOWN",
]

AuthorityType = Literal[
    "NONE",
    "ADVISORY",
    "REVIEW_REQUEST",
    "OPERATOR_REVIEW_RECEIPT",
    "OPERATOR_APPROVAL_EVIDENCE",
    "PROOF_EVIDENCE",
    "GPP_PERMIT",
    "UEAK_ADMISSION",
    "EXECUTION_RECEIPT",
    "UNKNOWN",
]

OperatorLossiness = Literal[
    "LOSSLESS",
    "LOSSY_DISCLOSED",
    "LOSSY_UNDISCLOSED_FORBIDDEN",
    "UNKNOWN",
]

TranslationDecisionOutcome = Literal[
    "ACCEPT_DIRECT",
    "ACCEPT_TRANSLATED",
    "ACCEPT_APPROXIMATE_WITH_WARNING",
    "ROUTE_TO_REVIEW",
    "REJECT_NAKED_CLAIM",
    "REJECT_NOT_TRANSLATABLE",
    "REJECT_UNSUPPORTED",
    "FAIL_CLOSED",
]

AUTHORITY_FRAMES = frozenset(
    {"PERMIT_AUTHORITY", "EXECUTION_AUTHORITY", "EXTERNAL_ACTION", "PUBLICATION"}
)
AUTHORITY_BEARING_FIELDS = frozenset(
    {
        "authority_semantics",
        "identity_ref",
        "scope_ref",
        "freshness_ref",
        "required_authority_chain_refs",
    }
)
AUTHORITY_LATTICE: dict[str, int] = {
    "UEAK_ADMISSION": 7,
    "GPP_PERMIT": 6,
    "EXECUTION_RECEIPT": 5,
    "OPERATOR_APPROVAL_EVIDENCE": 4,
    "OPERATOR_REVIEW_RECEIPT": 3,
    "PROOF_EVIDENCE": 2,
    "REVIEW_REQUEST": 1,
    "ADVISORY": 0,
    "NONE": 0,
    "UNKNOWN": -1,
}

OBSERVATION_ENVELOPE_FIELDS = (
    "observed_context",
    "visible_inputs",
    "hidden_or_unavailable_inputs",
    "sampling_conditions",
    "threshold_conditions",
    "operational_constraints",
    "model_or_rule_version",
    "tool_access",
    "memory_access",
    "context_window",
    "retry_policy",
    "inference_budget",
    "scaffold_or_runtime",
    "judge_or_evaluator",
    "safety_filters",
    "human_intervention",
    "trace_depth",
    "failure_recovery_semantics",
    "uncertainty_sources",
    "missingness",
    "known_limitations",
)


def _normalize_enum(value: str, allowed: frozenset[str]) -> str:
    if value in allowed:
        return value
    return "UNKNOWN"


def _validate_no_secrets(*parts: str) -> None:
    blocked = ("password", "api_key", "secret", "token=")
    for part in parts:
        lower = part.lower()
        for needle in blocked:
            if needle in lower:
                raise TEPValidationError("tep.validation.secret", "secret-like material forbidden in TEP records")


@dataclass(frozen=True)
class ReferenceCondition:
    reference_id: str
    target_decision_frame: TargetDecisionFrame
    comparison_scope: str
    expected_units_or_semantics: str
    required_translation_inputs: tuple[str, ...]
    authority_required: AuthorityRequired
    freshness_required: bool
    identity_required: bool
    scope_required: bool
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.target_decision_frame in AUTHORITY_FRAMES and self.authority_required not in (
            "GPP_PERMIT",
            "UEAK_ADMISSION",
            "OPERATOR_IAM_APPROVAL",
        ):
            raise TEPValidationError(
                "tep.validation.reference_condition",
                "authority-bearing frames require governed authority_required",
            )
        _validate_no_secrets(
            self.reference_id,
            self.comparison_scope,
            self.expected_units_or_semantics,
            *self.required_translation_inputs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-reference-condition",
            "schema_version": TEP_SCHEMA_VERSION,
            "reference_id": self.reference_id,
            "target_decision_frame": self.target_decision_frame,
            "comparison_scope": self.comparison_scope,
            "expected_units_or_semantics": self.expected_units_or_semantics,
            "required_translation_inputs": list(self.required_translation_inputs),
            "authority_required": self.authority_required,
            "freshness_required": self.freshness_required,
            "identity_required": self.identity_required,
            "scope_required": self.scope_required,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ObservationEnvelope:
    observed_context: str
    visible_inputs: tuple[str, ...]
    hidden_or_unavailable_inputs: tuple[str, ...]
    sampling_conditions: str
    threshold_conditions: str
    operational_constraints: str
    model_or_rule_version: str
    tool_access: tuple[str, ...]
    memory_access: str
    context_window: str
    retry_policy: str
    inference_budget: str
    scaffold_or_runtime: str
    judge_or_evaluator: str
    safety_filters: str
    human_intervention: str
    trace_depth: str
    failure_recovery_semantics: str
    uncertainty_sources: tuple[str, ...]
    missingness: str
    known_limitations: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.observed_context,
            self.sampling_conditions,
            self.threshold_conditions,
            self.operational_constraints,
            self.model_or_rule_version,
            self.memory_access,
            self.context_window,
            self.retry_policy,
            self.inference_budget,
            self.scaffold_or_runtime,
            self.judge_or_evaluator,
            self.safety_filters,
            self.human_intervention,
            self.trace_depth,
            self.failure_recovery_semantics,
            self.missingness,
            *self.visible_inputs,
            *self.hidden_or_unavailable_inputs,
            *self.tool_access,
            *self.uncertainty_sources,
            *self.known_limitations,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def field_value(self, name: str) -> Any:
        if name not in OBSERVATION_ENVELOPE_FIELDS:
            return None
        value = getattr(self, name)
        if isinstance(value, tuple):
            return list(value)
        return value

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-observation-envelope",
            "schema_version": TEP_SCHEMA_VERSION,
            "observed_context": self.observed_context,
            "visible_inputs": list(self.visible_inputs),
            "hidden_or_unavailable_inputs": list(self.hidden_or_unavailable_inputs),
            "sampling_conditions": self.sampling_conditions,
            "threshold_conditions": self.threshold_conditions,
            "operational_constraints": self.operational_constraints,
            "model_or_rule_version": self.model_or_rule_version,
            "tool_access": list(self.tool_access),
            "memory_access": self.memory_access,
            "context_window": self.context_window,
            "retry_policy": self.retry_policy,
            "inference_budget": self.inference_budget,
            "scaffold_or_runtime": self.scaffold_or_runtime,
            "judge_or_evaluator": self.judge_or_evaluator,
            "safety_filters": self.safety_filters,
            "human_intervention": self.human_intervention,
            "trace_depth": self.trace_depth,
            "failure_recovery_semantics": self.failure_recovery_semantics,
            "uncertainty_sources": list(self.uncertainty_sources),
            "missingness": self.missingness,
            "known_limitations": list(self.known_limitations),
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class UncertaintySemantics:
    uncertainty_type: UncertaintyType
    ambiguity: str
    missingness: str
    unsupported_regions: tuple[str, ...]
    stale_regions: tuple[str, ...]
    confidence_interval: tuple[float, float] | None = None
    calibration_ref: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.ambiguity, self.missingness, self.calibration_ref, *self.unsupported_regions, *self.stale_regions)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-uncertainty-semantics",
            "schema_version": TEP_SCHEMA_VERSION,
            "uncertainty_type": self.uncertainty_type,
            "ambiguity": self.ambiguity,
            "missingness": self.missingness,
            "unsupported_regions": list(self.unsupported_regions),
            "stale_regions": list(self.stale_regions),
        }
        if self.confidence_interval is not None:
            payload["confidence_interval"] = list(self.confidence_interval)
        if self.calibration_ref:
            payload["calibration_ref"] = self.calibration_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AuthoritySemantics:
    authority_type: AuthorityType
    may_authorize_execution: bool
    may_mint_permit: bool
    may_call_oea_ter: bool
    may_grant_tools: bool
    may_grant_memory: bool
    may_grant_context: bool
    may_publish: bool
    downstream_allowed_uses: tuple[str, ...]
    downstream_forbidden_uses: tuple[str, ...]
    required_authority_chain_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.may_grant_tools or self.may_grant_memory or self.may_grant_context:
            raise TEPValidationError(
                "tep.validation.authority_semantics",
                "may_grant_tools/memory/context are pinned false",
            )
        if self.may_authorize_execution and self.authority_type != "UEAK_ADMISSION":
            raise TEPValidationError(
                "tep.validation.authority_semantics",
                "may_authorize_execution requires UEAK_ADMISSION",
            )
        if self.may_authorize_execution and not self.required_authority_chain_refs:
            raise TEPValidationError(
                "tep.validation.authority_semantics",
                "may_authorize_execution requires authority chain refs",
            )
        if self.may_mint_permit:
            raise TEPValidationError(
                "tep.validation.authority_semantics",
                "TEP records cannot mint permits",
            )
        _validate_no_secrets(
            *self.downstream_allowed_uses,
            *self.downstream_forbidden_uses,
            *self.required_authority_chain_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-authority-semantics",
            "schema_version": TEP_SCHEMA_VERSION,
            "authority_type": self.authority_type,
            "may_authorize_execution": self.may_authorize_execution,
            "may_mint_permit": self.may_mint_permit,
            "may_call_oea_ter": self.may_call_oea_ter,
            "may_grant_tools": self.may_grant_tools,
            "may_grant_memory": self.may_grant_memory,
            "may_grant_context": self.may_grant_context,
            "may_publish": self.may_publish,
            "downstream_allowed_uses": list(self.downstream_allowed_uses),
            "downstream_forbidden_uses": list(self.downstream_forbidden_uses),
            "required_authority_chain_refs": list(self.required_authority_chain_refs),
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class LossCertificate:
    loss_certificate_id: str
    compression_method: str
    fields_preserved: tuple[str, ...]
    fields_discarded: tuple[str, ...]
    expected_effect: str
    invalid_comparisons: tuple[str, ...]
    audit_ref: str
    raw_envelope_pointer: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.invalid_comparisons:
            raise TEPValidationError(
                "tep.validation.loss_certificate",
                "invalid_comparisons is required for confession",
            )
        for field_name in self.fields_discarded:
            if field_name in AUTHORITY_BEARING_FIELDS:
                raise TEPValidationError(
                    "tep.validation.loss_certificate",
                    f"authority-bearing field discarded: {field_name}",
                )
        _validate_no_secrets(
            self.loss_certificate_id,
            self.compression_method,
            self.expected_effect,
            self.audit_ref,
            self.raw_envelope_pointer,
            *self.fields_preserved,
            *self.fields_discarded,
            *self.invalid_comparisons,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-loss-certificate",
            "schema_version": TEP_SCHEMA_VERSION,
            "loss_certificate_id": self.loss_certificate_id,
            "compression_method": self.compression_method,
            "fields_preserved": list(self.fields_preserved),
            "fields_discarded": list(self.fields_discarded),
            "expected_effect": self.expected_effect,
            "invalid_comparisons": list(self.invalid_comparisons),
            "audit_ref": self.audit_ref,
        }
        if self.raw_envelope_pointer:
            payload["raw_envelope_pointer"] = self.raw_envelope_pointer
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class TranslationOperator:
    operator_id: str
    from_claim_type: ClaimType
    to_reference_condition: str
    required_input_fields: tuple[str, ...]
    supported_envelope_conditions: tuple[str, ...]
    unsupported_conditions: tuple[str, ...]
    transformation_description: str
    deterministic: bool
    lossiness: OperatorLossiness
    validation_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    version: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.lossiness in ("LOSSY_UNDISCLOSED_FORBIDDEN", "UNKNOWN"):
            raise TEPValidationError(
                "tep.validation.translation_operator",
                f"forbidden operator lossiness: {self.lossiness}",
            )
        if not self.validation_refs:
            raise TEPValidationError(
                "tep.validation.translation_operator",
                "operators require validation_refs",
            )
        _validate_no_secrets(
            self.operator_id,
            self.to_reference_condition,
            self.transformation_description,
            self.version,
            *self.required_input_fields,
            *self.supported_envelope_conditions,
            *self.unsupported_conditions,
            *self.validation_refs,
            *self.proof_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-translation-operator",
            "schema_version": TEP_SCHEMA_VERSION,
            "operator_id": self.operator_id,
            "from_claim_type": self.from_claim_type,
            "to_reference_condition": self.to_reference_condition,
            "required_input_fields": list(self.required_input_fields),
            "supported_envelope_conditions": list(self.supported_envelope_conditions),
            "unsupported_conditions": list(self.unsupported_conditions),
            "transformation_description": self.transformation_description,
            "deterministic": self.deterministic,
            "lossiness": self.lossiness,
            "validation_refs": list(self.validation_refs),
            "proof_refs": list(self.proof_refs),
            "version": self.version,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_type: ClaimType
    scalar_value: float | None = None
    structured_value: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.scalar_value is None and self.structured_value is None:
            raise TEPValidationError("tep.validation.claim", "claim requires scalar_value or structured_value")
        _validate_no_secrets(self.claim_id)


@dataclass(frozen=True)
class TranslationEnvelope:
    envelope_id: str
    claim_id: str
    claim_type: ClaimType
    producer_ref: str
    producer_module: str
    producer_role: str
    reference_condition: ReferenceCondition
    observation_envelope: ObservationEnvelope
    uncertainty_semantics: UncertaintySemantics
    authority_semantics: AuthoritySemantics
    trace_pointer: str
    proof_refs: tuple[str, ...]
    translation_status: TranslationStatus
    created_at: str
    scalar_value: float | None = None
    structured_value: dict[str, Any] | None = None
    translation_operator_ref: str = ""
    compression_method: str = ""
    loss_certificate: LossCertificate | None = None
    not_translatable_reason: str = ""
    freshness_ref: str = ""
    identity_ref: str = ""
    scope_ref: str = ""
    expires_at: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.scalar_value is None and self.structured_value is None:
            raise TEPValidationError("tep.validation.envelope", "envelope requires scalar_value or structured_value")
        if self.translation_status == "NOT_TRANSLATABLE" and not self.not_translatable_reason:
            raise TEPValidationError(
                "tep.validation.envelope",
                "NOT_TRANSLATABLE requires not_translatable_reason",
            )
        _validate_no_secrets(
            self.envelope_id,
            self.claim_id,
            self.producer_ref,
            self.producer_module,
            self.producer_role,
            self.trace_pointer,
            self.translation_operator_ref,
            self.compression_method,
            self.not_translatable_reason,
            self.freshness_ref,
            self.identity_ref,
            self.scope_ref,
            *self.proof_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-translation-envelope",
            "schema_version": TEP_SCHEMA_VERSION,
            "envelope_id": self.envelope_id,
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "producer_ref": self.producer_ref,
            "producer_module": self.producer_module,
            "producer_role": self.producer_role,
            "reference_condition": self.reference_condition.to_payload(include_hash=True),
            "observation_envelope": self.observation_envelope.to_payload(include_hash=True),
            "uncertainty_semantics": self.uncertainty_semantics.to_payload(include_hash=True),
            "authority_semantics": self.authority_semantics.to_payload(include_hash=True),
            "trace_pointer": self.trace_pointer,
            "proof_refs": list(self.proof_refs),
            "translation_status": self.translation_status,
            "created_at": self.created_at,
            "authority_created": False,
        }
        if self.scalar_value is not None:
            payload["scalar_value"] = self.scalar_value
        if self.structured_value is not None:
            payload["structured_value"] = self.structured_value
        if self.translation_operator_ref:
            payload["translation_operator_ref"] = self.translation_operator_ref
        if self.compression_method:
            payload["compression_method"] = self.compression_method
        if self.loss_certificate is not None:
            payload["loss_certificate"] = self.loss_certificate.to_payload(include_hash=True)
        if self.not_translatable_reason:
            payload["not_translatable_reason"] = self.not_translatable_reason
        if self.freshness_ref:
            payload["freshness_ref"] = self.freshness_ref
        if self.identity_ref:
            payload["identity_ref"] = self.identity_ref
        if self.scope_ref:
            payload["scope_ref"] = self.scope_ref
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class TranslationDecision:
    decision_id: str
    input_claim_ref: str
    input_envelope_ref: str
    target_reference_condition: str
    decision: TranslationDecisionOutcome
    reason: str
    warnings: tuple[str, ...] = ()
    output_claim_ref: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.reason:
            raise TEPValidationError("tep.validation.decision", "reason is required")
        _validate_no_secrets(
            self.decision_id,
            self.input_claim_ref,
            self.input_envelope_ref,
            self.target_reference_condition,
            self.reason,
            self.output_claim_ref,
            *self.warnings,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "tep-translation-decision",
            "schema_version": TEP_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "input_claim_ref": self.input_claim_ref,
            "input_envelope_ref": self.input_envelope_ref,
            "target_reference_condition": self.target_reference_condition,
            "decision": self.decision,
            "reason": self.reason,
            "warnings": list(self.warnings),
            "authority_created": False,
        }
        if self.output_claim_ref:
            payload["output_claim_ref"] = self.output_claim_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


__all__ = [
    "AUTHORITY_BEARING_FIELDS",
    "AUTHORITY_FRAMES",
    "AUTHORITY_LATTICE",
    "AuthorityRequired",
    "AuthoritySemantics",
    "AuthorityType",
    "Claim",
    "ClaimType",
    "FIXTURE_CLOCK",
    "LossCertificate",
    "OBSERVATION_ENVELOPE_FIELDS",
    "ObservationEnvelope",
    "OperatorLossiness",
    "ReferenceCondition",
    "TEP_SCHEMA_VERSION",
    "TargetDecisionFrame",
    "TranslationDecision",
    "TranslationDecisionOutcome",
    "TranslationEnvelope",
    "TranslationOperator",
    "TranslationStatus",
    "UncertaintySemantics",
    "UncertaintyType",
    "_normalize_enum",
]
