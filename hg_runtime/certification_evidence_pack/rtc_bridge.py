"""CRT RTC event drafts — policy safety, no authority."""

from __future__ import annotations

from typing import Any


from hg_core.boundary_full.rtc_emit import boundary_draft


def certification_snapshot_requested(*, snapshot_id: str, branch: str, head: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_CERTIFICATION_SNAPSHOT_REQUESTED",
        {"snapshot_id": snapshot_id, "branch": branch, "head": head},
    )


def safety_claim_registered(*, claim_id: str, status: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_SAFETY_CLAIM_REGISTERED",
        {"claim_id": claim_id, "status": status, "record_hash": record_hash},
    )


def control_mapping_recorded(*, claim_id: str, control_domain: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_CONTROL_MAPPING_RECORDED",
        {"claim_id": claim_id, "control_domain": control_domain},
    )


def evidence_reference_added(*, evidence_id: str, path: str, content_hash: str, fresh: bool) -> dict[str, Any]:
    return boundary_draft(
        "CRT_EVIDENCE_REFERENCE_ADDED",
        {
            "evidence_id": evidence_id,
            "path": path,
            "content_hash": content_hash,
            "fresh": fresh,
        },
    )


def exception_recorded(*, exception_id: str, control_domain: str, record_hash: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_EXCEPTION_RECORDED",
        {"exception_id": exception_id, "control_domain": control_domain, "record_hash": record_hash},
    )


def unsupported_claim_detected(*, claim_id: str, statement: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_UNSUPPORTED_CLAIM_DETECTED",
        {"claim_id": claim_id, "statement": statement},
    )


def fake_green_prevented(*, claim_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_FAKE_GREEN_PREVENTED",
        {"claim_id": claim_id, "reason_code": reason_code},
    )


def auditor_export_created(*, export_id: str, bundle_hash: str, snapshot_id: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_AUDITOR_EXPORT_CREATED",
        {"export_id": export_id, "bundle_hash": bundle_hash, "snapshot_id": snapshot_id},
    )


def signal_refused(*, snapshot_id: str, reason_code: str) -> dict[str, Any]:
    return boundary_draft(
        "CRT_SIGNAL_REFUSED",
        {"snapshot_id": snapshot_id, "reason_code": reason_code},
    )


__all__ = [
    "auditor_export_created",
    "certification_snapshot_requested",
    "control_mapping_recorded",
    "evidence_reference_added",
    "exception_recorded",
    "fake_green_prevented",
    "safety_claim_registered",
    "signal_refused",
    "unsupported_claim_detected",
]
