"""Integration adapters — produce action requests, never execute."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.schema import ExcitonControlKind, ExcitonControlRequest
from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.risk import classify_action_risk
from hg_runtime.exciton_action_model.schema import (
    FIXTURE_UTC,
    AgentActionRequest,
    AgentActionStatus,
    AgentActionSurface,
    new_action_id,
)
from hg_runtime.exciton_action_model.validation import default_surface_for_action

_CONTROL_TO_ACTION: dict[ExcitonControlKind, AgentActionType] = {
    ExcitonControlKind.REFRESH_STATUS: AgentActionType.STATUS_REFRESH,
    ExcitonControlKind.OPEN_PROOF_LINK: AgentActionType.PROOF_OPEN,
    ExcitonControlKind.ADD_OPERATOR_NOTE: AgentActionType.OPERATOR_NOTE,
    ExcitonControlKind.STOP_AGENT: AgentActionType.PANIC_STOP,
    ExcitonControlKind.PANIC_STOP: AgentActionType.PANIC_STOP,
    ExcitonControlKind.STOP_SOAK: AgentActionType.STOP_SOAK,
    ExcitonControlKind.GENERATE_SOCIAL_DRAFT: AgentActionType.SOCIAL_DRAFT,
    ExcitonControlKind.QUEUE_SOCIAL_DRAFT: AgentActionType.SOCIAL_DRAFT,
    ExcitonControlKind.APPROVE_SOCIAL_PUBLISH: AgentActionType.SOCIAL_POST,
    ExcitonControlKind.REFRESH_SOCIAL_STATUS: AgentActionType.SOCIAL_READ,
}


def _base_request(
    action_type: AgentActionType,
    *,
    source_agent: str = "agent0",
    source_task: str = "",
    title: str = "",
    human_summary: str = "",
    sanitized_preview: str = "",
    raw_payload_ref: str | None = None,
    status: AgentActionStatus = AgentActionStatus.QUEUED,
    priority: int = 0,
) -> AgentActionRequest:
    req = AgentActionRequest(
        action_id=new_action_id(),
        action_type=action_type,
        source_agent=source_agent,
        source_task=source_task,
        created_at=FIXTURE_UTC,
        priority=priority,
        status=status,
        title=title or action_type.value.replace("_", " ").title(),
        human_summary=human_summary or f"Action request: {action_type.value}",
        sanitized_preview=sanitized_preview or human_summary or action_type.value,
        requested_surface=default_surface_for_action(action_type),
        risk_class=classify_action_risk(action_type),
        raw_payload_ref=raw_payload_ref,
    )
    # Force hash computation via to_payload side effect
    req.item_hash = req.to_payload()["item_hash"]
    return req


def from_social_draft(
    *,
    draft_id: str,
    surface_id: str,
    preview: str,
    source_task: str = "",
    source_agent: str = "agent0",
) -> AgentActionRequest:
    return _base_request(
        AgentActionType.SOCIAL_DRAFT,
        source_agent=source_agent,
        source_task=source_task or draft_id,
        title="Social draft",
        human_summary=f"Draft social post for {surface_id}",
        sanitized_preview=preview[:500],
        raw_payload_ref=f".hg-local/social/drafts/{draft_id}.json",
        status=AgentActionStatus.DRY_RUN_ONLY,
    )


def from_social_publish_request(
    *,
    draft_id: str,
    surface_id: str,
    preview: str,
    source_task: str = "",
    source_agent: str = "agent0",
) -> AgentActionRequest:
    return _base_request(
        AgentActionType.SOCIAL_POST,
        source_agent=source_agent,
        source_task=source_task or draft_id,
        title="Social publish request",
        human_summary=f"Publish social post to {surface_id} (operator review required)",
        sanitized_preview=preview[:500],
        raw_payload_ref=f".hg-local/social/drafts/{draft_id}.json",
        status=AgentActionStatus.QUEUED,
    )


def from_web_action_request(
    *,
    action_type: AgentActionType,
    url: str,
    summary: str = "",
    source_task: str = "",
    source_agent: str = "agent0",
) -> AgentActionRequest:
    safe_url = url.split("?")[0][:200]
    return _base_request(
        action_type,
        source_agent=source_agent,
        source_task=source_task,
        title=f"Web action: {action_type.value}",
        human_summary=summary or f"Web action on {safe_url}",
        sanitized_preview=safe_url,
        raw_payload_ref=f".hg-local/web/requests/{new_action_id()}.json",
    )


def from_tool_request(
    *,
    tool_id: str,
    summary: str,
    source_task: str = "",
    source_agent: str = "agent0",
    payload_ref: str | None = None,
) -> AgentActionRequest:
    ref = payload_ref or f".hg-local/tools/requests/{tool_id}.json"
    return _base_request(
        AgentActionType.TOOL_EXECUTE,
        source_agent=source_agent,
        source_task=source_task or tool_id,
        title=f"Tool execute: {tool_id}",
        human_summary=summary,
        sanitized_preview=summary[:500],
        raw_payload_ref=ref,
    )


def from_exciton_control_request(request: ExcitonControlRequest) -> AgentActionRequest:
    action_type = _CONTROL_TO_ACTION.get(request.control, AgentActionType.OPERATOR_NOTE)
    summary = f"EXCITON control {request.control.value} from {request.operator}"
    return _base_request(
        action_type,
        source_agent="agent0",
        source_task=request.request_id,
        title=request.control.value.replace("_", " ").title(),
        human_summary=summary,
        sanitized_preview=summary,
        raw_payload_ref=f".hg-local/exciton/controls/{request.request_id}.json",
    )


def to_operator_queue_item_stub(request: AgentActionRequest) -> dict[str, Any]:
    """Non-executing queue item projection for future operator queue runtime."""
    payload = request.to_payload()
    return {
        "schema": "operator-queue-item-stub",
        "action_id": payload["action_id"],
        "action_type": payload["action_type"],
        "status": payload["status"],
        "title": payload["title"],
        "human_summary": payload["human_summary"],
        "sanitized_preview": payload["sanitized_preview"],
        "risk_class": payload["risk_class"],
        "item_hash": payload["item_hash"],
        "executable": False,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = [
    "from_exciton_control_request",
    "from_social_draft",
    "from_social_publish_request",
    "from_tool_request",
    "from_web_action_request",
    "to_operator_queue_item_stub",
]
