"""FCE RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import boundary_draft


def signal_received(*, signal_id: str, content_ref: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_SIGNAL_RECEIVED",
        {"signal_id": signal_id, "content_ref": content_ref, "record_hash": record_hash},
    )


def signal_classified(*, signal_id: str, capability_class: str, confidence: float) -> dict[str, Any]:
    return boundary_draft(
        "FCE_SIGNAL_CLASSIFIED",
        {"signal_id": signal_id, "capability_class": capability_class, "confidence": confidence},
    )


def dangerous_capability_detected(*, signal_id: str, capability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_DANGEROUS_CAPABILITY_DETECTED",
        {"signal_id": signal_id, "capability_class": capability_class},
    )


def autonomous_chain_risk_detected(*, signal_id: str, capability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_AUTONOMOUS_CHAIN_RISK_DETECTED",
        {"signal_id": signal_id, "capability_class": capability_class},
    )


def social_engineering_risk_detected(*, signal_id: str, capability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_SOCIAL_ENGINEERING_RISK_DETECTED",
        {"signal_id": signal_id, "capability_class": capability_class},
    )


def supply_chain_risk_detected(*, signal_id: str, capability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_SUPPLY_CHAIN_RISK_DETECTED",
        {"signal_id": signal_id, "capability_class": capability_class},
    )


def capability_eval_recorded(*, signal_id: str, record_hash: str, capability_class: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_CAPABILITY_EVAL_RECORDED",
        {"signal_id": signal_id, "record_hash": record_hash, "capability_class": capability_class},
    )


def refusal_recommended(*, signal_id: str, capability_class: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_REFUSAL_RECOMMENDED",
        {"signal_id": signal_id, "capability_class": capability_class, "reason_code": reason_code},
    )


def operator_review_recommended(*, signal_id: str, capability_class: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_OPERATOR_REVIEW_RECOMMENDED",
        {"signal_id": signal_id, "capability_class": capability_class, "reason_code": reason_code},
    )


def signal_refused(*, signal_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "FCE_SIGNAL_REFUSED",
        {"signal_id": signal_id, "reason_code": reason_code},
    )


__all__ = [
    "autonomous_chain_risk_detected",
    "capability_eval_recorded",
    "dangerous_capability_detected",
    "operator_review_recommended",
    "refusal_recommended",
    "signal_classified",
    "signal_received",
    "signal_refused",
    "social_engineering_risk_detected",
    "supply_chain_risk_detected",
]
