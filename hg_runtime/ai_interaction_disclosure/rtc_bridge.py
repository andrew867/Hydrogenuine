"""AID RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any, Optional


from hg_core.boundary_full.rtc_emit import boundary_draft


def disclosure_created(*, disclosure_id: str, record_hash: str, runtime_mode: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_DISCLOSURE_CREATED",
        {"disclosure_id": disclosure_id, "record_hash": record_hash, "runtime_mode": runtime_mode},
    )


def mode_card_recorded(*, mode_card_id: str, interaction_id: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_MODE_CARD_RECORDED",
        {"mode_card_id": mode_card_id, "interaction_id": interaction_id, "record_hash": record_hash},
    )


def capability_limits_recorded(*, limit_card_id: str, interaction_id: str, status: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_CAPABILITY_LIMITS_RECORDED",
        {"limit_card_id": limit_card_id, "interaction_id": interaction_id, "status": status},
    )


def uncertainty_disclosed(*, uncertainty_id: str, interaction_id: str, trl_feed_status: str, sab_feed_status: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_UNCERTAINTY_DISCLOSED",
        {
            "uncertainty_id": uncertainty_id,
            "interaction_id": interaction_id,
            "trl_feed_status": trl_feed_status,
            "sab_feed_status": sab_feed_status,
        },
    )


def generated_content_disclosed(
    *,
    content_disclosure_id: str,
    interaction_id: str,
    syn_feed_status: str,
    syn_artifact_id: Optional[str] = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "content_disclosure_id": content_disclosure_id,
        "interaction_id": interaction_id,
        "syn_feed_status": syn_feed_status,
    }
    if syn_artifact_id:
        body["syn_artifact_id"] = syn_artifact_id
    return boundary_draft("AID_GENERATED_CONTENT_DISCLOSED", body)


def disclosure_missing_detected(*, interaction_id: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_DISCLOSURE_MISSING_DETECTED",
        {"interaction_id": interaction_id},
    )


def operator_education_recommended(*, interaction_id: str, reason: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_OPERATOR_EDUCATION_RECOMMENDED",
        {"interaction_id": interaction_id, "reason": reason},
    )


def signal_refused(*, interaction_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "AID_SIGNAL_REFUSED",
        {"interaction_id": interaction_id, "reason_code": reason_code},
    )


__all__ = [
    "capability_limits_recorded",
    "disclosure_created",
    "disclosure_missing_detected",
    "generated_content_disclosed",
    "mode_card_recorded",
    "operator_education_recommended",
    "signal_refused",
    "uncertainty_disclosed",
]
