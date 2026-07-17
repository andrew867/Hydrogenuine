"""External visibility contract for publish receipts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from hg_runtime.social_capability.schema import SocialSurface


class ExternalVisibilityStatus(str, Enum):
    CONFIRMED_URL = "confirmed_url"
    REMOTE_ID_ONLY = "remote_id_only"
    GOVERNANCE_ONLY_NO_EXTERNAL_URL = "governance_only_no_external_url"
    FIXTURE_ONLY = "fixture_only"
    MANUAL_SURFACE_NO_URL = "manual_surface_no_url"
    FAILED_NO_REMOTE_EVIDENCE = "failed_no_remote_evidence"


def build_visibility_contract(
    *,
    surface: SocialSurface,
    published: bool,
    fixture_mode: bool,
    published_url: str | None = None,
    remote_id: str | None = None,
    queue_item_ref: str | None = None,
    approval_receipt_ref: str | None = None,
    permit_id: str | None = None,
) -> dict[str, Any]:
    if fixture_mode:
        status = ExternalVisibilityStatus.FIXTURE_ONLY
        url_reason = "fixture_mode"
        remote_reason = "fixture_mode"
    elif surface == SocialSurface.CUSTOM_MANUAL_POST:
        status = ExternalVisibilityStatus.MANUAL_SURFACE_NO_URL
        url_reason = "manual_surface_requires_operator_verification"
        remote_reason = "manual_surface_no_remote_id"
    elif published_url:
        status = ExternalVisibilityStatus.CONFIRMED_URL
        url_reason = None
        remote_reason = None if remote_id else "remote_id_not_recorded"
    elif remote_id:
        status = ExternalVisibilityStatus.REMOTE_ID_ONLY
        url_reason = "platform_url_not_available"
        remote_reason = None
    elif published:
        status = ExternalVisibilityStatus.GOVERNANCE_ONLY_NO_EXTERNAL_URL
        url_reason = "governance_layer_publish_without_platform_url"
        remote_reason = "remote_id_not_recorded"
    else:
        status = ExternalVisibilityStatus.FAILED_NO_REMOTE_EVIDENCE
        url_reason = "not_published"
        remote_reason = "not_published"

    return {
        "surface": surface.value,
        "publish_mode": "fixture" if fixture_mode else "live",
        "external_visibility_status": status.value,
        "published_url": published_url,
        "published_url_unavailable_reason": url_reason,
        "remote_id": remote_id,
        "remote_id_unavailable_reason": remote_reason,
        "queue_item_ref": queue_item_ref,
        "approval_receipt_ref": approval_receipt_ref,
        "permit_id": permit_id,
        "governance_publish_is_not_external_proof": True,
    }


def visibility_verdict(contract: dict[str, Any]) -> str:
    status = contract.get("external_visibility_status", "")
    if status == ExternalVisibilityStatus.CONFIRMED_URL.value:
        return "GREEN_PUBLISH_RECEIPT_URL_CONTRACT_READY"
    if status in (
        ExternalVisibilityStatus.GOVERNANCE_ONLY_NO_EXTERNAL_URL.value,
        ExternalVisibilityStatus.MANUAL_SURFACE_NO_URL.value,
        ExternalVisibilityStatus.REMOTE_ID_ONLY.value,
    ):
        return "YELLOW_PLATFORM_URL_UNAVAILABLE"
    if status == ExternalVisibilityStatus.FIXTURE_ONLY.value:
        return "GREEN_PUBLISH_RECEIPT_URL_CONTRACT_READY"
    return "RED_PUBLISHED_RECEIPT_WITHOUT_URL_CONTRACT"


__all__ = ["ExternalVisibilityStatus", "build_visibility_contract", "visibility_verdict"]
