"""TEP cluster validation errors — translation is not authority."""

from __future__ import annotations

NAKED_CLAIM_REFUSED = "tep.refused.naked_claim"
NOT_TRANSLATABLE = "tep.refused.not_translatable"
UNSUPPORTED_CLAIM = "tep.refused.unsupported"
AUTHORITY_CONVERSION_REFUSED = "tep.refused.authority_conversion"
COMPRESSION_LOSS_UNDISCLOSED = "tep.refused.compression_loss_undisclosed"
COMPRESSION_LOSS_INCOMPLETE = "tep.refused.compression_loss_incomplete"
AUTHORITY_FIELD_DISCARDED = "tep.refused.authority_field_discarded"
UNKNOWN_CLAIM_FAILED_CLOSED = "tep.refused.unknown_failed_closed"
ENVELOPE_INVALID = "tep.refused.envelope_invalid"
FALSE_COMPARABILITY_REFUSED = "tep.refused.false_comparability"
IDENTITY_SCOPE_REQUIRED = "tep.refused.identity_scope_required"
FRESHNESS_REQUIRED = "tep.refused.freshness_required"
CLAIM_TYPE_MISMATCH = "tep.refused.claim_type_mismatch"
UNCERTAINTY_TYPE_MISMATCH = "tep.refused.uncertainty_type_mismatch"
CLAIM_TYPE_MISMATCH = "tep.refused.claim_type_mismatch"
OPERATOR_FORBIDDEN_LOSSINESS = "tep.refused.operator_forbidden_lossiness"
AUTHORITY_SEMANTICS_INVALID = "tep.refused.authority_semantics_invalid"

TEP_CLAIM_RECEIVED = "tep.event.claim_received"
TEP_ENVELOPE_VALIDATED = "tep.event.envelope_validated"
TEP_NAKED_CLAIM_REFUSED = "tep.event.naked_claim_refused"
TEP_TRANSLATION_OPERATOR_SELECTED = "tep.event.translation_operator_selected"
TEP_TRANSLATION_ACCEPTED = "tep.event.translation_accepted"
TEP_TRANSLATION_REFUSED = "tep.event.translation_refused"
TEP_APPROXIMATE_LOSSY_ACCEPTED_WITH_WARNING = "tep.event.approximate_lossy_accepted_with_warning"
TEP_NOT_TRANSLATABLE_RECORDED = "tep.event.not_translatable_recorded"
TEP_AUTHORITY_SEMANTICS_VALIDATED = "tep.event.authority_semantics_validated"
TEP_AUTHORITY_CONVERSION_REFUSED = "tep.event.authority_conversion_refused"
TEP_COMPRESSION_LOSS_RECORDED = "tep.event.compression_loss_recorded"
TEP_CLAIM_ROUTED_TO_REVIEW = "tep.event.claim_routed_to_review"
TEP_UNKNOWN_CLAIM_FAILED_CLOSED = "tep.event.unknown_claim_failed_closed"


class TEPValidationError(ValueError):
    """Raised when TEP records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "AUTHORITY_CONVERSION_REFUSED",
    "AUTHORITY_FIELD_DISCARDED",
    "AUTHORITY_SEMANTICS_INVALID",
    "CLAIM_TYPE_MISMATCH",
    "CLAIM_TYPE_MISMATCH",
    "COMPRESSION_LOSS_INCOMPLETE",
    "COMPRESSION_LOSS_UNDISCLOSED",
    "ENVELOPE_INVALID",
    "FALSE_COMPARABILITY_REFUSED",
    "FRESHNESS_REQUIRED",
    "IDENTITY_SCOPE_REQUIRED",
    "NAKED_CLAIM_REFUSED",
    "NOT_TRANSLATABLE",
    "OPERATOR_FORBIDDEN_LOSSINESS",
    "TEP_APPROXIMATE_LOSSY_ACCEPTED_WITH_WARNING",
    "TEP_AUTHORITY_CONVERSION_REFUSED",
    "TEP_AUTHORITY_SEMANTICS_VALIDATED",
    "TEP_CLAIM_RECEIVED",
    "TEP_CLAIM_ROUTED_TO_REVIEW",
    "TEP_COMPRESSION_LOSS_RECORDED",
    "TEP_ENVELOPE_VALIDATED",
    "TEP_NAKED_CLAIM_REFUSED",
    "TEP_NOT_TRANSLATABLE_RECORDED",
    "TEP_TRANSLATION_ACCEPTED",
    "TEP_TRANSLATION_OPERATOR_SELECTED",
    "TEP_TRANSLATION_REFUSED",
    "TEP_UNKNOWN_CLAIM_FAILED_CLOSED",
    "TEPValidationError",
    "UNCERTAINTY_TYPE_MISMATCH",
    "UNKNOWN_CLAIM_FAILED_CLOSED",
    "UNSUPPORTED_CLAIM",
]
