"""TEP validators — fail closed on missing envelope or authority inflation."""

from __future__ import annotations

from typing import Any

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.tep_cluster.errors import (
    AUTHORITY_CONVERSION_REFUSED,
    AUTHORITY_FIELD_DISCARDED,
    AUTHORITY_SEMANTICS_INVALID,
    CLAIM_TYPE_MISMATCH,
    COMPRESSION_LOSS_INCOMPLETE,
    COMPRESSION_LOSS_UNDISCLOSED,
    ENVELOPE_INVALID,
    FALSE_COMPARABILITY_REFUSED,
    FRESHNESS_REQUIRED,
    IDENTITY_SCOPE_REQUIRED,
    NAKED_CLAIM_REFUSED,
    OPERATOR_FORBIDDEN_LOSSINESS,
    TEPValidationError,
    UNCERTAINTY_TYPE_MISMATCH,
    UNKNOWN_CLAIM_FAILED_CLOSED,
)
from hg_runtime.translation_envelope_protocol.types import (
    AUTHORITY_BEARING_FIELDS,
    AUTHORITY_FRAMES,
    AUTHORITY_LATTICE,
    AuthoritySemantics,
    Claim,
    LossCertificate,
    ObservationEnvelope,
    ReferenceCondition,
    TranslationEnvelope,
    TranslationOperator,
    UncertaintySemantics,
)


def is_naked_claim(
    claim: Claim,
    envelope: TranslationEnvelope | None,
) -> tuple[bool, str]:
    if envelope is None:
        return True, "no TranslationEnvelope present"
    if envelope.claim_id != claim.claim_id:
        return True, "envelope claim_id mismatch"
    if envelope.compression_method and envelope.loss_certificate is None:
        return True, "compressed claim without loss certificate"
    return False, ""


def validate_authority_semantics(semantics: AuthoritySemantics) -> None:
    try:
        AuthoritySemantics(
            authority_type=semantics.authority_type,
            may_authorize_execution=semantics.may_authorize_execution,
            may_mint_permit=semantics.may_mint_permit,
            may_call_oea_ter=semantics.may_call_oea_ter,
            may_grant_tools=semantics.may_grant_tools,
            may_grant_memory=semantics.may_grant_memory,
            may_grant_context=semantics.may_grant_context,
            may_publish=semantics.may_publish,
            downstream_allowed_uses=semantics.downstream_allowed_uses,
            downstream_forbidden_uses=semantics.downstream_forbidden_uses,
            required_authority_chain_refs=semantics.required_authority_chain_refs,
        )
    except TEPValidationError as exc:
        raise TEPValidationError(AUTHORITY_SEMANTICS_INVALID, str(exc)) from exc


def validate_loss_certificate(certificate: LossCertificate) -> None:
    if not certificate.invalid_comparisons:
        raise TEPValidationError(COMPRESSION_LOSS_INCOMPLETE, "invalid_comparisons required")
    for field_name in certificate.fields_discarded:
        if field_name in AUTHORITY_BEARING_FIELDS:
            raise TEPValidationError(AUTHORITY_FIELD_DISCARDED, f"discarded {field_name}")


def validate_translation_envelope(envelope: TranslationEnvelope) -> None:
    validate_authority_semantics(envelope.authority_semantics)
    if envelope.translation_status == "UNKNOWN":
        raise TEPValidationError(UNKNOWN_CLAIM_FAILED_CLOSED, "translation_status UNKNOWN")
    if envelope.compression_method:
        if envelope.loss_certificate is None:
            raise TEPValidationError(COMPRESSION_LOSS_UNDISCLOSED, "undisclosed compression loss")
        validate_loss_certificate(envelope.loss_certificate)


def observation_field_equivalent(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    if isinstance(left, list) and isinstance(right, list):
        return sorted(left) == sorted(right)
    return left == right


def envelope_equivalent_for_frame(
    left: ObservationEnvelope,
    right: ObservationEnvelope,
    *,
    required_inputs: tuple[str, ...],
) -> bool:
    for field_name in required_inputs:
        if not observation_field_equivalent(left.field_value(field_name), right.field_value(field_name)):
            return False
    return True


FRAME_CLAIM_TYPES: dict[str, frozenset[str]] = {
    "RISK_POSTURE": frozenset({"RISK_SCORE", "SEVERITY_SCORE"}),
    "PRIORITIZATION": frozenset({"PRIORITY_SCORE", "GOAL_FIT"}),
    "TRUST_CALIBRATION": frozenset({"TRUST_SCORE", "CALIBRATION_SCORE"}),
    "REVIEW": frozenset({"OPERATOR_REVIEW_RECEIPT", "OPERATOR_APPROVAL_EVIDENCE"}),
    "PROOF": frozenset({"PROOF_SUMMARY", "RESEARCH_EVIDENCE"}),
    "PERMIT_AUTHORITY": frozenset({"PERMIT_DECISION"}),
    "EXECUTION_AUTHORITY": frozenset({"EXECUTION_ADMISSION"}),
}


def envelopes_directly_comparable(
    claim: Claim,
    envelope: TranslationEnvelope,
    target: ReferenceCondition,
    *,
    peer_observation: ObservationEnvelope | None = None,
) -> tuple[bool, str]:
    if claim.claim_type == "UNKNOWN" or envelope.claim_type == "UNKNOWN":
        return False, "unknown claim type"
    if claim.claim_type != envelope.claim_type:
        return False, "claim/envelope claim_type mismatch"
    allowed_types = FRAME_CLAIM_TYPES.get(target.target_decision_frame)
    if allowed_types is not None and claim.claim_type not in allowed_types:
        return False, CLAIM_TYPE_MISMATCH
    if envelope.uncertainty_semantics.uncertainty_type == "UNKNOWN":
        return False, "unknown uncertainty type"
    if envelope.reference_condition.target_decision_frame != target.target_decision_frame:
        return False, "reference frame mismatch"
    if envelope.reference_condition.comparison_scope != target.comparison_scope:
        return False, "comparison scope mismatch"
    if peer_observation is not None:
        if not envelope_equivalent_for_frame(
            envelope.observation_envelope,
            peer_observation,
            required_inputs=target.required_translation_inputs,
        ):
            return False, "observation envelope not equivalent"
    elif not envelope_equivalent_for_frame(
        envelope.observation_envelope,
        envelope.observation_envelope,
        required_inputs=target.required_translation_inputs,
    ):
        return False, "observation envelope incomplete for frame"
    return True, ""


def uncertainty_types_comparable(
    left: UncertaintySemantics,
    right: UncertaintySemantics,
) -> bool:
    if left.uncertainty_type == "UNKNOWN" or right.uncertainty_type == "UNKNOWN":
        return False
    return left.uncertainty_type == right.uncertainty_type


def authority_meets_frame(
    semantics: AuthoritySemantics,
    target: ReferenceCondition,
) -> bool:
    required = target.authority_required
    if required == "NONE":
        return True
    if required == "REVIEW_ONLY":
        return semantics.authority_type in (
            "REVIEW_REQUEST",
            "OPERATOR_REVIEW_RECEIPT",
            "OPERATOR_APPROVAL_EVIDENCE",
            "PROOF_EVIDENCE",
            "GPP_PERMIT",
            "UEAK_ADMISSION",
        )
    if required == "OPERATOR_IAM_APPROVAL":
        return semantics.authority_type in ("OPERATOR_APPROVAL_EVIDENCE", "GPP_PERMIT", "UEAK_ADMISSION")
    if required == "GPP_PERMIT":
        return semantics.authority_type in ("GPP_PERMIT", "UEAK_ADMISSION")
    if required == "UEAK_ADMISSION":
        return semantics.authority_type == "UEAK_ADMISSION" and semantics.may_authorize_execution
    return False


def authority_conversion_refused(
    semantics: AuthoritySemantics,
    target: ReferenceCondition,
) -> tuple[bool, str]:
    if target.target_decision_frame not in AUTHORITY_FRAMES:
        return False, ""
    if semantics.authority_type in ("GPP_PERMIT", "UEAK_ADMISSION"):
        return False, ""
    if semantics.authority_type == "OPERATOR_REVIEW_RECEIPT" and target.target_decision_frame == "PERMIT_AUTHORITY":
        return True, "review receipt cannot become permit"
    if semantics.authority_type == "PROOF_EVIDENCE" and target.target_decision_frame in (
        "PERMIT_AUTHORITY",
        "EXECUTION_AUTHORITY",
    ):
        return True, "proof evidence is not permit or admission"
    if semantics.authority_type == "ADVISORY" and target.authority_required in (
        "GPP_PERMIT",
        "UEAK_ADMISSION",
    ):
        return True, "advisory claim cannot satisfy authority frame"
    return False, ""


def check_identity_scope_requirements(
    envelope: TranslationEnvelope,
    target: ReferenceCondition,
) -> tuple[bool, str]:
    if target.identity_required and not envelope.identity_ref:
        return False, IDENTITY_SCOPE_REQUIRED
    if target.scope_required and not envelope.scope_ref:
        return False, IDENTITY_SCOPE_REQUIRED
    if envelope.claim_type == "OPERATOR_APPROVAL_EVIDENCE" and (
        not envelope.identity_ref or not envelope.scope_ref
    ):
        return False, IDENTITY_SCOPE_REQUIRED
    return True, ""


def check_freshness_requirements(
    envelope: TranslationEnvelope,
    target: ReferenceCondition,
    *,
    observed_at: str,
) -> tuple[bool, str]:
    if not target.freshness_required:
        return True, ""
    if not envelope.freshness_ref:
        return False, FRESHNESS_REQUIRED
    if envelope.expires_at and envelope.expires_at < observed_at:
        return False, FRESHNESS_REQUIRED
    stale = envelope.uncertainty_semantics.stale_regions
    if stale:
        return False, FRESHNESS_REQUIRED
    return True, ""


def operator_supports_envelope(
    operator: TranslationOperator,
    envelope: TranslationEnvelope,
) -> tuple[bool, str]:
    if operator.lossiness in ("LOSSY_UNDISCLOSED_FORBIDDEN", "UNKNOWN"):
        return False, OPERATOR_FORBIDDEN_LOSSINESS
    for condition in operator.unsupported_conditions:
        if condition in envelope.observation_envelope.observed_context:
            return False, f"unsupported condition: {condition}"
    for field_name in operator.required_input_fields:
        value = envelope.observation_envelope.field_value(field_name)
        if value in (None, "", [], ()):
            return False, f"missing required input: {field_name}"
    return True, ""


def select_translation_operator(
    claim: Claim,
    envelope: TranslationEnvelope,
    target: ReferenceCondition,
    operators: tuple[TranslationOperator, ...],
) -> TranslationOperator | None:
    matches: list[TranslationOperator] = []
    for operator in operators:
        if operator.from_claim_type != claim.claim_type:
            continue
        if operator.to_reference_condition != target.reference_id:
            continue
        ok, _ = operator_supports_envelope(operator, envelope)
        if ok:
            matches.append(operator)
    if not matches:
        return None
    return sorted(matches, key=lambda op: (op.version, op.operator_id))[0]


def authority_downgrade_only(
    before: AuthoritySemantics,
    after: AuthoritySemantics,
) -> bool:
    before_rank = AUTHORITY_LATTICE.get(before.authority_type, -1)
    after_rank = AUTHORITY_LATTICE.get(after.authority_type, -1)
    if after_rank > before_rank:
        return False
    flags = (
        "may_authorize_execution",
        "may_mint_permit",
        "may_call_oea_ter",
        "may_grant_tools",
        "may_grant_memory",
        "may_grant_context",
        "may_publish",
    )
    for flag in flags:
        if getattr(after, flag) and not getattr(before, flag):
            return False
    return True


def decision_id_for(
    claim: Claim,
    envelope: TranslationEnvelope | None,
    target: ReferenceCondition,
) -> str:
    body = {
        "claim_id": claim.claim_id,
        "claim_type": claim.claim_type,
        "scalar_value": claim.scalar_value,
        "structured_value": claim.structured_value,
        "envelope_hash": envelope.record_hash if envelope else None,
        "target_reference_id": target.reference_id,
    }
    return f"tep-decision:{canonical_hash(body)}"


__all__ = [
    "authority_conversion_refused",
    "authority_downgrade_only",
    "authority_meets_frame",
    "check_freshness_requirements",
    "check_identity_scope_requirements",
    "decision_id_for",
    "envelope_equivalent_for_frame",
    "envelopes_directly_comparable",
    "is_naked_claim",
    "observation_field_equivalent",
    "operator_supports_envelope",
    "select_translation_operator",
    "uncertainty_types_comparable",
    "validate_authority_semantics",
    "validate_loss_certificate",
    "validate_translation_envelope",
]
