"""CDO RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import boundary_draft


def compromise_signal_received(*, signal_id: str, content_ref: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_COMPROMISE_SIGNAL_RECEIVED",
        {"signal_id": signal_id, "content_ref": content_ref, "record_hash": record_hash},
    )


def disconnection_signal_received(*, signal_id: str, content_ref: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_DISCONNECTION_SIGNAL_RECEIVED",
        {"signal_id": signal_id, "content_ref": content_ref, "record_hash": record_hash},
    )


def isolation_posture_selected(*, signal_id: str, posture: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_ISOLATION_POSTURE_SELECTED",
        {
            "signal_id": signal_id,
            "posture": posture,
            "record_hash": record_hash,
            "posture_is_not_permission": True,
        },
    )


def network_suspected(*, signal_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_NETWORK_SUSPECTED",
        {"signal_id": signal_id, "external_action_recommended": False},
    )


def provider_suspected(*, signal_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_PROVIDER_SUSPECTED",
        {"signal_id": signal_id, "external_action_recommended": False},
    )


def operator_channel_stale(*, signal_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_OPERATOR_CHANNEL_STALE",
        {"signal_id": signal_id, "operator_channel_fresh": False},
    )


def local_replay_only_entered(*, signal_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_LOCAL_REPLAY_ONLY_ENTERED",
        {"signal_id": signal_id, "local_replay_only": True, "external_action_recommended": False},
    )


def evidence_preservation_recommended(*, signal_id: str, posture: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_EVIDENCE_PRESERVATION_RECOMMENDED",
        {"signal_id": signal_id, "posture": posture, "append_only": True},
    )


def safe_mode_recommended(*, signal_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_SAFE_MODE_RECOMMENDED",
        {"signal_id": signal_id, "external_action_recommended": False},
    )


def recovery_runbook_recommended(*, signal_id: str, posture: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_RECOVERY_RUNBOOK_RECOMMENDED",
        {
            "signal_id": signal_id,
            "posture": posture,
            "recovery_is_not_execution": True,
            "external_action_recommended": False,
        },
    )


def signal_refused(*, signal_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "CDO_SIGNAL_REFUSED",
        {"signal_id": signal_id, "reason_code": reason_code},
    )


__all__ = [
    "compromise_signal_received",
    "disconnection_signal_received",
    "evidence_preservation_recommended",
    "isolation_posture_selected",
    "local_replay_only_entered",
    "network_suspected",
    "operator_channel_stale",
    "provider_suspected",
    "recovery_runbook_recommended",
    "safe_mode_recommended",
    "signal_refused",
]
