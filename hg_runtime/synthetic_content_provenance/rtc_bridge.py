"""SYN RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import boundary_draft


def content_artifact_registered(*, artifact_id: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_CONTENT_ARTIFACT_REGISTERED",
        {"artifact_id": artifact_id, "record_hash": record_hash},
    )


def provenance_recorded(*, artifact_id: str, provenance_id: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_PROVENANCE_RECORDED",
        {"artifact_id": artifact_id, "provenance_id": provenance_id, "record_hash": record_hash},
    )


def disclosure_label_attached(*, artifact_id: str, label_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_DISCLOSURE_LABEL_ATTACHED",
        {"artifact_id": artifact_id, "label_id": label_id, "risk_class": risk_class},
    )


def watermark_metadata_recorded(*, artifact_id: str, watermark_ref: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_WATERMARK_METADATA_RECORDED",
        {"artifact_id": artifact_id, "watermark_ref": watermark_ref, "is_safety_proof": False},
    )


def deepfake_risk_detected(*, artifact_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_DEEPFAKE_RISK_DETECTED",
        {"artifact_id": artifact_id, "risk_class": risk_class},
    )


def impersonation_risk_detected(*, artifact_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_IMPERSONATION_RISK_DETECTED",
        {"artifact_id": artifact_id, "risk_class": risk_class},
    )


def export_receipt_recorded(*, receipt_id: str, artifact_id: str, artifact_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_EXPORT_RECEIPT_RECORDED",
        {"receipt_id": receipt_id, "artifact_id": artifact_id, "artifact_hash": artifact_hash},
    )


def undisclosed_content_refused(*, artifact_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_UNDISCLOSED_CONTENT_REFUSED",
        {"artifact_id": artifact_id, "reason_code": reason_code},
    )


def operator_review_recommended(*, artifact_id: str, risk_class: str) -> dict[str, Any]:
    return boundary_draft(
        "SYN_OPERATOR_REVIEW_RECOMMENDED",
        {"artifact_id": artifact_id, "risk_class": risk_class},
    )


__all__ = [
    "content_artifact_registered",
    "deepfake_risk_detected",
    "disclosure_label_attached",
    "export_receipt_recorded",
    "impersonation_risk_detected",
    "operator_review_recommended",
    "provenance_recorded",
    "undisclosed_content_refused",
    "watermark_metadata_recorded",
]
