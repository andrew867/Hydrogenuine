"""ORI receipt validator — IAM-bound approval evidence only."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry, resolve_operator_id
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.ori_cluster.errors import (
    INERT_BARE_OPERATOR_REF,
    INERT_MISSING_EXPIRY,
    INERT_MISSING_OPERATOR_REF,
    INERT_MISSING_SCOPE,
    INERT_OPERATOR_REVOKED,
    INERT_OUT_OF_SCOPE,
    INERT_UNREGISTERED_OPERATOR_REF,
    ORI_APPROVAL_EVIDENCE_BOUND,
    ORI_RECEIPT_RECORDED,
    REFUSED_ORI_AS_AUTHORITY,
    REFUSED_STALE_APPROVAL_RECEIPT,
    OriValidationError,
)
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.time.expiry import validate_approval_window
from hg_runtime.operator_review_intake.types import (
    OperatorReviewReceipt,
    is_approval_evidence_action,
    is_bare_operator_ref,
)


def refuse_ori_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise OriValidationError(
            REFUSED_ORI_AS_AUTHORITY,
            "operator review receipt cannot become authority",
        )


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def evaluate_operator_review_receipt(
    receipt: OperatorReviewReceipt,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate receipt; approval-evidence actions require IAM-bound operator + scope + expiry."""
    if treat_as_authority:
        refuse_ori_as_authority(treat_as_authority=True)

    if not is_approval_evidence_action(receipt.operator_action):
        return _base_result(
            status="recorded",
            reason_code=ORI_RECEIPT_RECORDED,
            receipt_id=receipt.receipt_id,
            operator_action=receipt.operator_action,
            evidence_admissible=False,
        )

    if not receipt.operator_ref:
        return _base_result(
            status="inert",
            reason_code=INERT_MISSING_OPERATOR_REF,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    if is_bare_operator_ref(receipt.operator_ref):
        return _base_result(
            status="inert",
            reason_code=INERT_BARE_OPERATOR_REF,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    scope = receipt.resolved_scope()
    if not scope:
        return _base_result(
            status="inert",
            reason_code=INERT_MISSING_SCOPE,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    if scope not in AUTHORITY_SCOPES:
        return _base_result(
            status="inert",
            reason_code=INERT_OUT_OF_SCOPE,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    if not receipt.approval_expires_at:
        return _base_result(
            status="inert",
            reason_code=INERT_MISSING_EXPIRY,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    ok_window, window_reason = validate_approval_window(receipt.approval_expires_at, observed_at)
    if not ok_window:
        return _base_result(
            status="inert",
            reason_code=REFUSED_STALE_APPROVAL_RECEIPT,
            detail=window_reason,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    reg = registry or load_registry()
    resolved = resolve_operator_id(receipt.operator_ref, registry=reg)
    if resolved is None:
        return _base_result(
            status="inert",
            reason_code=INERT_UNREGISTERED_OPERATOR_REF,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    auth = validate_operator_authority(
        receipt.operator_ref,
        scope=scope,
        registry=reg,
        record_event=False,
    )
    if not auth.ok:
        reason = INERT_OPERATOR_REVOKED if auth.reason_code == "denied.operator_revoked" else INERT_OUT_OF_SCOPE
        if auth.reason_code == "denied.unregistered_operator":
            reason = INERT_UNREGISTERED_OPERATOR_REF
        return _base_result(
            status="inert",
            reason_code=reason,
            iam_reason=auth.reason_code,
            receipt_id=receipt.receipt_id,
            evidence_admissible=False,
        )

    binding = auth.binding
    return _base_result(
        status="recorded",
        reason_code=ORI_APPROVAL_EVIDENCE_BOUND,
        receipt_id=receipt.receipt_id,
        evidence_admissible=True,
        iam_binding=binding.to_payload() if binding else None,
        resolved_operator_id=auth.resolved_operator_id,
        approval_scope=scope,
    )


__all__ = [
    "evaluate_operator_review_receipt",
    "refuse_ori_as_authority",
]
