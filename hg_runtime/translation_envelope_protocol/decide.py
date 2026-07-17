"""TEP pure decision function — translation is not authority."""

from __future__ import annotations

from hg_core.tep_cluster.errors import (
    AUTHORITY_CONVERSION_REFUSED,
    CLAIM_TYPE_MISMATCH,
    FALSE_COMPARABILITY_REFUSED,
    NAKED_CLAIM_REFUSED,
    NOT_TRANSLATABLE,
    TEP_APPROXIMATE_LOSSY_ACCEPTED_WITH_WARNING,
    TEP_AUTHORITY_CONVERSION_REFUSED,
    TEP_CLAIM_ROUTED_TO_REVIEW,
    TEP_COMPRESSION_LOSS_RECORDED,
    TEP_ENVELOPE_VALIDATED,
    TEP_NAKED_CLAIM_REFUSED,
    TEP_NOT_TRANSLATABLE_RECORDED,
    TEP_TRANSLATION_ACCEPTED,
    TEP_TRANSLATION_OPERATOR_SELECTED,
    TEP_UNKNOWN_CLAIM_FAILED_CLOSED,
    UNCERTAINTY_TYPE_MISMATCH,
    UNKNOWN_CLAIM_FAILED_CLOSED,
    UNSUPPORTED_CLAIM,
)
from hg_runtime.translation_envelope_protocol.types import (
    AUTHORITY_FRAMES,
    Claim,
    ReferenceCondition,
    TranslationDecision,
    TranslationEnvelope,
    TranslationOperator,
)
from hg_runtime.translation_envelope_protocol.validator import (
    authority_conversion_refused,
    authority_meets_frame,
    check_freshness_requirements,
    check_identity_scope_requirements,
    decision_id_for,
    envelopes_directly_comparable,
    is_naked_claim,
    select_translation_operator,
    uncertainty_types_comparable,
    validate_translation_envelope,
)


def _make_decision(
    claim: Claim,
    envelope: TranslationEnvelope | None,
    target: ReferenceCondition,
    outcome: str,
    reason: str,
    *,
    warnings: tuple[str, ...] = (),
    output_claim_ref: str = "",
    event_code: str = "",
) -> TranslationDecision:
    return TranslationDecision(
        decision_id=decision_id_for(claim, envelope, target),
        input_claim_ref=claim.claim_id,
        input_envelope_ref=envelope.envelope_id if envelope else "",
        target_reference_condition=target.reference_id,
        decision=outcome,  # type: ignore[arg-type]
        reason=reason if not event_code else f"{reason} [{event_code}]",
        warnings=warnings,
        output_claim_ref=output_claim_ref,
    )


def tep_decide(
    claim: Claim,
    envelope: TranslationEnvelope | None,
    target_reference_condition: ReferenceCondition,
    *,
    operators: tuple[TranslationOperator, ...] = (),
    observed_at: str = "2026-06-14T03:00:00.000000Z",
    peer_observation=None,
) -> TranslationDecision:
    """Pure deterministic comparability decision. Never performs I/O or grants authority."""
    naked, naked_reason = is_naked_claim(claim, envelope)
    if naked:
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "REJECT_NAKED_CLAIM",
            naked_reason,
            event_code=TEP_NAKED_CLAIM_REFUSED,
        )

    assert envelope is not None

    try:
        validate_translation_envelope(envelope)
    except Exception as exc:
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "FAIL_CLOSED",
            str(exc),
            event_code=TEP_UNKNOWN_CLAIM_FAILED_CLOSED,
        )

    identity_ok, identity_reason = check_identity_scope_requirements(envelope, target_reference_condition)
    if not identity_ok:
        if target_reference_condition.target_decision_frame in AUTHORITY_FRAMES:
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "ROUTE_TO_REVIEW",
                identity_reason,
                event_code=TEP_CLAIM_ROUTED_TO_REVIEW,
            )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "FAIL_CLOSED",
            identity_reason,
            event_code=UNKNOWN_CLAIM_FAILED_CLOSED,
        )

    freshness_ok, freshness_reason = check_freshness_requirements(
        envelope,
        target_reference_condition,
        observed_at=observed_at,
    )
    if not freshness_ok:
        if target_reference_condition.target_decision_frame in AUTHORITY_FRAMES:
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "ROUTE_TO_REVIEW",
                freshness_reason,
                event_code=TEP_CLAIM_ROUTED_TO_REVIEW,
            )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "FAIL_CLOSED",
            freshness_reason,
            event_code=UNKNOWN_CLAIM_FAILED_CLOSED,
        )

    if envelope.translation_status == "NOT_TRANSLATABLE":
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "REJECT_NOT_TRANSLATABLE",
            envelope.not_translatable_reason or NOT_TRANSLATABLE,
            event_code=TEP_NOT_TRANSLATABLE_RECORDED,
        )

    if envelope.translation_status == "UNSUPPORTED":
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "REJECT_UNSUPPORTED",
            UNSUPPORTED_CLAIM,
            event_code=TEP_UNKNOWN_CLAIM_FAILED_CLOSED,
        )

    if envelope.translation_status == "UNKNOWN":
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "FAIL_CLOSED",
            UNKNOWN_CLAIM_FAILED_CLOSED,
            event_code=TEP_UNKNOWN_CLAIM_FAILED_CLOSED,
        )

    refused, conversion_reason = authority_conversion_refused(
        envelope.authority_semantics,
        target_reference_condition,
    )
    if refused:
        if target_reference_condition.target_decision_frame in AUTHORITY_FRAMES:
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "ROUTE_TO_REVIEW",
                conversion_reason,
                event_code=TEP_AUTHORITY_CONVERSION_REFUSED,
            )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "REJECT_NOT_TRANSLATABLE",
            conversion_reason,
            event_code=AUTHORITY_CONVERSION_REFUSED,
        )

    if claim.claim_type != envelope.claim_type:
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "FAIL_CLOSED",
            CLAIM_TYPE_MISMATCH,
            event_code=FALSE_COMPARABILITY_REFUSED,
        )

    comparable, compare_reason = envelopes_directly_comparable(
        claim,
        envelope,
        target_reference_condition,
        peer_observation=peer_observation,
    )
    if comparable and envelope.translation_status in ("DIRECTLY_COMPARABLE", "TRANSLATED"):
        if not authority_meets_frame(envelope.authority_semantics, target_reference_condition):
            if target_reference_condition.target_decision_frame in AUTHORITY_FRAMES:
                return _make_decision(
                    claim,
                    envelope,
                    target_reference_condition,
                    "ROUTE_TO_REVIEW",
                    "authority semantics do not meet frame requirement",
                    event_code=TEP_CLAIM_ROUTED_TO_REVIEW,
                )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "ACCEPT_DIRECT",
            "envelope equivalent for target frame",
            output_claim_ref=claim.claim_id,
            event_code=TEP_ENVELOPE_VALIDATED,
        )

    if envelope.translation_status == "APPROXIMATE_LOSSY":
        if envelope.loss_certificate is None:
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "REJECT_NAKED_CLAIM",
                "lossy compression without certificate",
                event_code=TEP_NAKED_CLAIM_REFUSED,
            )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "ACCEPT_APPROXIMATE_WITH_WARNING",
            "approximate lossy comparison with disclosed certificate",
            warnings=(
                "lossy comparison",
                *envelope.loss_certificate.invalid_comparisons,
            ),
            output_claim_ref=claim.claim_id,
            event_code=TEP_COMPRESSION_LOSS_RECORDED,
        )

    operator = select_translation_operator(
        claim,
        envelope,
        target_reference_condition,
        operators,
    )
    if operator is not None:
        if operator.lossiness == "LOSSY_DISCLOSED":
            if envelope.loss_certificate is None:
                return _make_decision(
                    claim,
                    envelope,
                    target_reference_condition,
                    "REJECT_NAKED_CLAIM",
                    "lossy operator requires loss certificate",
                    event_code=TEP_NAKED_CLAIM_REFUSED,
                )
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "ACCEPT_APPROXIMATE_WITH_WARNING",
                f"operator {operator.operator_id} applied with disclosed loss",
                warnings=("lossy translation", *envelope.loss_certificate.invalid_comparisons),
                output_claim_ref=f"{claim.claim_id}:translated:{operator.operator_id}",
                event_code=TEP_APPROXIMATE_LOSSY_ACCEPTED_WITH_WARNING,
            )
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "ACCEPT_TRANSLATED",
            f"operator {operator.operator_id} applied",
            output_claim_ref=f"{claim.claim_id}:translated:{operator.operator_id}",
            event_code=TEP_TRANSLATION_OPERATOR_SELECTED,
        )

    if compare_reason:
        if "uncertainty" in compare_reason or claim.claim_type != envelope.claim_type:
            return _make_decision(
                claim,
                envelope,
                target_reference_condition,
                "REJECT_NOT_TRANSLATABLE",
                compare_reason or FALSE_COMPARABILITY_REFUSED,
                event_code=TEP_NOT_TRANSLATABLE_RECORDED,
            )

    if not uncertainty_types_comparable(
        envelope.uncertainty_semantics,
        envelope.uncertainty_semantics,
    ):
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "REJECT_NOT_TRANSLATABLE",
            UNCERTAINTY_TYPE_MISMATCH,
            event_code=FALSE_COMPARABILITY_REFUSED,
        )

    if target_reference_condition.target_decision_frame in AUTHORITY_FRAMES:
        return _make_decision(
            claim,
            envelope,
            target_reference_condition,
            "ROUTE_TO_REVIEW",
            "claim could matter but cannot be auto-translated into authority frame",
            event_code=TEP_CLAIM_ROUTED_TO_REVIEW,
        )

    return _make_decision(
        claim,
        envelope,
        target_reference_condition,
        "REJECT_NOT_TRANSLATABLE",
        compare_reason or NOT_TRANSLATABLE,
        event_code=TEP_NOT_TRANSLATABLE_RECORDED,
    )


__all__ = ["tep_decide"]
