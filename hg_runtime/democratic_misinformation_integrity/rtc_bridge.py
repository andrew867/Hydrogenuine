"""DMI RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import boundary_draft


def public_influence_signal_received(*, signal_id: str, content_ref: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_PUBLIC_INFLUENCE_SIGNAL_RECEIVED",
        {"signal_id": signal_id, "content_ref": content_ref, "record_hash": record_hash},
    )


def election_content_detected(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_ELECTION_CONTENT_DETECTED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def institutional_impersonation_detected(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_INSTITUTIONAL_IMPERSONATION_DETECTED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def deceptive_source_risk_detected(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_DECEPTIVE_SOURCE_RISK_DETECTED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def synthetic_public_figure_risk_detected(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_SYNTHETIC_PUBLIC_FIGURE_RISK_DETECTED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def misinformation_claim_check_recorded(
    *, signal_id: str, evidence_gap: bool, adjudicates_truth: bool = False
) -> dict[str, Any]:
    return boundary_draft(
        "DMI_MISINFORMATION_CLAIM_CHECK_RECORDED",
        {
            "signal_id": signal_id,
            "evidence_gap": evidence_gap,
            "adjudicates_truth": adjudicates_truth,
            "claim_check_only": True,
        },
    )


def disclosure_required(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_DISCLOSURE_REQUIRED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def refusal_recommended(*, signal_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_REFUSAL_RECOMMENDED",
        {"signal_id": signal_id, "reason_code": reason_code, "recommendation_is_not_permission": True},
    )


def operator_review_recommended(*, signal_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_OPERATOR_REVIEW_RECOMMENDED",
        {"signal_id": signal_id, "risk_class": risk_class},
    )


def signal_refused(*, signal_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "DMI_SIGNAL_REFUSED",
        {"signal_id": signal_id, "reason_code": reason_code},
    )


__all__ = [
    "deceptive_source_risk_detected",
    "disclosure_required",
    "election_content_detected",
    "institutional_impersonation_detected",
    "misinformation_claim_check_recorded",
    "operator_review_recommended",
    "public_influence_signal_received",
    "refusal_recommended",
    "signal_refused",
    "synthetic_public_figure_risk_detected",
]
