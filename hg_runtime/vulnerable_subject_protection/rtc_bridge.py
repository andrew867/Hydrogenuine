"""VSP RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import boundary_draft


def signal_received(*, signal_id: str, content_ref: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_SIGNAL_RECEIVED",
        {"signal_id": signal_id, "content_ref": content_ref, "record_hash": record_hash},
    )


def vulnerability_classified(*, signal_id: str, vulnerability_class: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_VULNERABILITY_CLASSIFIED",
        {
            "signal_id": signal_id,
            "vulnerability_class": vulnerability_class,
            "record_hash": record_hash,
            "inferred_only": True,
        },
    )


def minor_risk_detected(*, signal_id: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_MINOR_RISK_DETECTED",
        {"signal_id": signal_id, "vulnerability_class": vulnerability_class},
    )


def crisis_adjacent_risk_detected(*, signal_id: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_CRISIS_ADJACENT_RISK_DETECTED",
        {"signal_id": signal_id, "vulnerability_class": vulnerability_class},
    )


def dependency_risk_detected(*, signal_id: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_DEPENDENCY_RISK_DETECTED",
        {"signal_id": signal_id, "vulnerability_class": vulnerability_class},
    )


def sensitive_interaction_recorded(*, signal_id: str, record_hash: str, content_ref: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_SENSITIVE_INTERACTION_RECORDED",
        {"signal_id": signal_id, "record_hash": record_hash, "content_ref": content_ref, "redacted": True},
    )


def protective_boundary_applied(*, signal_id: str, recommendation: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_PROTECTIVE_BOUNDARY_APPLIED",
        {
            "signal_id": signal_id,
            "recommendation": recommendation,
            "vulnerability_class": vulnerability_class,
            "recommendation_is_not_permission": True,
        },
    )


def escalation_recommended(*, signal_id: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_ESCALATION_RECOMMENDED",
        {
            "signal_id": signal_id,
            "vulnerability_class": vulnerability_class,
            "escalation_hint_only": True,
            "diagnosis_fields": False,
        },
    )


def retention_limit_recommended(*, signal_id: str, vulnerability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_RETENTION_LIMIT_RECOMMENDED",
        {
            "signal_id": signal_id,
            "vulnerability_class": vulnerability_class,
            "retention_recommendation_only": True,
        },
    )


def signal_refused(*, signal_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "VSP_SIGNAL_REFUSED",
        {"signal_id": signal_id, "reason_code": reason_code},
    )


__all__ = [
    "crisis_adjacent_risk_detected",
    "dependency_risk_detected",
    "escalation_recommended",
    "minor_risk_detected",
    "protective_boundary_applied",
    "retention_limit_recommended",
    "sensitive_interaction_recorded",
    "signal_received",
    "signal_refused",
    "vulnerability_classified",
]
