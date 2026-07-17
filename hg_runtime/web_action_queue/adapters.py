"""Adapters between web actions and operator queue / action model."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.risk import classify_action_risk
from hg_runtime.exciton_action_model.schema import (
    AgentActionRequest,
    AgentActionStatus,
    AgentActionSurface,
    FIXTURE_UTC,
    new_action_id,
)
from hg_runtime.operator_action_queue.schema import OperatorQueueItem, new_queue_item_id
from hg_runtime.web_action_queue.action_types import WEB_TO_AGENT_ACTION, WebActionType
from hg_runtime.web_action_queue.schema import WebActionRequest, WebCargoSummary, new_web_action_id
from hg_runtime.web_action_queue.sanitization import WebActionSanitizer


def web_action_to_agent_action_request(web: WebActionRequest) -> AgentActionRequest:
    agent_type = WEB_TO_AGENT_ACTION.get(web.action_type, AgentActionType.WEB_READ_URL)
    status_map = {
        "queued": AgentActionStatus.QUEUED,
        "approved": AgentActionStatus.APPROVED,
        "denied": AgentActionStatus.DENIED,
        "dry_run_only": AgentActionStatus.DRY_RUN_ONLY,
        "blocked": AgentActionStatus.BLOCKED,
        "quarantined": AgentActionStatus.QUEUED,
        "executed_read_only": AgentActionStatus.EXECUTED,
    }
    req = AgentActionRequest(
        action_id=new_action_id(),
        action_type=agent_type,
        source_agent=web.source_agent,
        source_task=web.source_task or web.web_action_id,
        created_at=web.created_at,
        expires_at=web.expires_at,
        priority=0,
        status=status_map.get(web.status.value, AgentActionStatus.QUEUED),
        title=f"Web: {web.action_type.value}",
        human_summary=web.human_summary,
        sanitized_preview=web.sanitized_preview,
        raw_payload_ref=f".hg-local/web/requests/{web.web_action_id}.json",
        requested_surface=AgentActionSurface.WEB,
        risk_class=classify_action_risk(agent_type),
        trust_boundary_verdict=web.trust_boundary_verdict,
        policy_refs=list(web.policy_refs),
        proof_refs=list(web.proof_refs),
    )
    req.item_hash = req.to_payload()["item_hash"]
    return req


def web_action_to_operator_queue_item(web: WebActionRequest) -> OperatorQueueItem:
    ar = web_action_to_agent_action_request(web)
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=ar)
    item.refresh_hash()
    return item


def operator_queue_item_to_web_action_ref(item: OperatorQueueItem) -> dict[str, Any]:
    return {
        "operator_queue_item_id": item.queue_item_id,
        "action_id": item.action_id,
        "action_type": item.action_type,
        "status": item.status.value,
        "web_surface": "web",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _cargo(excerpt: str = "") -> WebCargoSummary:
    return WebCargoSummary(excerpt=excerpt, is_cargo=True)


def create_web_read_request(url: str, *, summary: str = "", cargo: str = "") -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_READ_URL,
        source_agent="agent0",
        source_task="web-read",
        created_at=FIXTURE_UTC,
        target_url=url,
        method="GET",
        human_summary=summary or f"Read URL {WebActionSanitizer.redact_url(url)}",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(cargo),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


def create_web_click_request(url: str, *, link_text: str = "", summary: str = "") -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_CLICK_LINK,
        source_agent="agent0",
        source_task="web-click",
        created_at=FIXTURE_UTC,
        target_url=url,
        link_text=link_text,
        human_summary=summary or f"Click link: {link_text or url}",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


def create_web_download_request(url: str, *, filename: str = "download.bin") -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_DOWNLOAD_FILE,
        source_agent="agent0",
        source_task="web-download",
        created_at=FIXTURE_UTC,
        target_url=url,
        download_filename=filename,
        human_summary=f"Download {filename}",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


def create_web_form_submit_request(url: str, *, fields: dict[str, str] | None = None) -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_FORM_SUBMIT,
        source_agent="agent0",
        source_task="web-form-submit",
        created_at=FIXTURE_UTC,
        target_url=url,
        method="POST",
        form_fields_summary=WebActionSanitizer.summarize_form_fields(fields),
        human_summary="Form submit request (denied by default)",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


def create_web_login_request(url: str) -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_LOGIN,
        source_agent="agent0",
        source_task="web-login",
        created_at=FIXTURE_UTC,
        target_url=url,
        human_summary="Login request (denied by default)",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


def create_web_purchase_request(url: str) -> WebActionRequest:
    return WebActionRequest(
        web_action_id=new_web_action_id(),
        action_type=WebActionType.WEB_PURCHASE,
        source_agent="agent0",
        source_task="web-purchase",
        created_at=FIXTURE_UTC,
        target_url=url,
        human_summary="Purchase request (denied by default)",
        sanitized_preview=WebActionSanitizer.redact_url(url) or "",
        cargo_summary=_cargo(),
        trust_boundary_verdict="GREEN_TRUST_OK",
    )


__all__ = [
    "create_web_click_request",
    "create_web_download_request",
    "create_web_form_submit_request",
    "create_web_login_request",
    "create_web_purchase_request",
    "create_web_read_request",
    "operator_queue_item_to_web_action_ref",
    "web_action_to_agent_action_request",
    "web_action_to_operator_queue_item",
]
