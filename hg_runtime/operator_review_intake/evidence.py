"""ORI approval evidence consumer — downstream refusal without IAM binding."""

from __future__ import annotations

from typing import Any

from hg_core.ori_cluster.errors import (
    INERT_BARE_OPERATOR_REF,
    INERT_MISSING_OPERATOR_REF,
    INERT_MISSING_SCOPE,
    INERT_OPERATOR_REVOKED,
    INERT_OUT_OF_SCOPE,
    INERT_UNREGISTERED_OPERATOR_REF,
    REFUSED_ORI_AS_AUTHORITY,
    REFUSED_STALE_APPROVAL_RECEIPT,
)
from hg_runtime.operator_review_intake.types import OperatorReviewReceipt, is_approval_evidence_action
from hg_runtime.operator_review_intake.validator import evaluate_operator_review_receipt

_INERT_REASONS = frozenset(
    {
        INERT_MISSING_OPERATOR_REF,
        INERT_BARE_OPERATOR_REF,
        INERT_UNREGISTERED_OPERATOR_REF,
        INERT_MISSING_SCOPE,
        INERT_OUT_OF_SCOPE,
        INERT_OPERATOR_REVOKED,
        REFUSED_STALE_APPROVAL_RECEIPT,
    }
)


def verify_ori_approval_evidence(
    receipt: OperatorReviewReceipt,
    *,
    observed_at: str,
    required_scope: str | None = None,
) -> dict[str, Any]:
    """Downstream choke point: ORI receipt alone is never sufficient for GPP/UEAK authority."""
    if not is_approval_evidence_action(receipt.operator_action):
        return {
            "admissible": False,
            "reason_code": "ori.evidence.not_approval_action",
            "permission_granted": False,
            "authority_created": False,
        }

    evaluated = evaluate_operator_review_receipt(receipt, observed_at=observed_at)
    if not evaluated.get("evidence_admissible"):
        return {
            "admissible": False,
            "reason_code": evaluated.get("reason_code", "ori.evidence.inert"),
            "permission_granted": False,
            "authority_created": False,
        }

    scope = receipt.resolved_scope()
    if required_scope and scope != required_scope:
        return {
            "admissible": False,
            "reason_code": INERT_OUT_OF_SCOPE,
            "permission_granted": False,
            "authority_created": False,
        }

    return {
        "admissible": True,
        "reason_code": evaluated.get("reason_code"),
        "permission_granted": False,
        "authority_created": False,
        "iam_binding": evaluated.get("iam_binding"),
        "ori_receipt_ref": receipt.receipt_id,
        "note": "ori_receipt_is_evidence_not_authority",
    }


def ori_receipt_is_not_permit_authority(receipt: OperatorReviewReceipt, *, observed_at: str) -> bool:
    """ORI approval evidence never carries permit-minting authority."""
    evidence = verify_ori_approval_evidence(receipt, observed_at=observed_at)
    return evidence.get("permission_granted") is False and evidence.get("authority_created") is False


def ori_receipt_is_not_ueak_admission_authority(receipt: OperatorReviewReceipt, *, observed_at: str) -> bool:
    """ORI approval evidence never carries UEAK admission authority."""
    return ori_receipt_is_not_permit_authority(receipt, observed_at=observed_at)


def refuse_ori_evidence_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_ORI_AS_AUTHORITY)


__all__ = [
    "_INERT_REASONS",
    "ori_receipt_is_not_permit_authority",
    "ori_receipt_is_not_ueak_admission_authority",
    "refuse_ori_evidence_as_authority",
    "verify_ori_approval_evidence",
]
