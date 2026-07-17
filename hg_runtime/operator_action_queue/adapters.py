"""Adapters bridging social review queue and action model to operator queue."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.schema import ExcitonControlRequest
from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.schema import AgentActionRequest, AgentActionStatus
from hg_runtime.exciton_action_model.adapters import (
    from_exciton_control_request as _from_exciton_control,
    from_social_draft as _from_social_draft,
    from_social_publish_request as _from_social_publish,
    from_tool_request as _from_tool,
)
from hg_runtime.exciton_action_model.risk import classify_action_risk
from hg_runtime.exciton_action_model.validation import default_surface_for_action
from hg_runtime.operator_action_queue.schema import OperatorQueueItem, new_queue_item_id
from hg_runtime.social_capability.review_schema import SocialReviewItem, SocialReviewStatus

_STATUS_MAP = {
    SocialReviewStatus.QUEUED: AgentActionStatus.QUEUED,
    SocialReviewStatus.APPROVED: AgentActionStatus.APPROVED,
    SocialReviewStatus.DENIED: AgentActionStatus.DENIED,
    SocialReviewStatus.EXPIRED: AgentActionStatus.EXPIRED,
    SocialReviewStatus.INVALID: AgentActionStatus.INVALID,
    SocialReviewStatus.PUBLISHED: AgentActionStatus.EXECUTED,
    SocialReviewStatus.PUBLISHED_LEGACY_UNCONFIRMED: AgentActionStatus.EXECUTED,
}


def from_social_review_item(item: SocialReviewItem) -> OperatorQueueItem:
    action_type = AgentActionType.SOCIAL_POST
    status = _STATUS_MAP.get(item.status, AgentActionStatus.QUEUED)
    req = AgentActionRequest(
        action_id=item.draft_id,
        action_type=action_type,
        source_agent="agent0",
        source_task=item.source_task_ref,
        created_at=item.created_at,
        priority=0,
        status=status,
        title=f"Social post ({item.surface_id})",
        human_summary=f"Social review item for {item.surface_id}",
        sanitized_preview=item.sanitized_preview,
        requested_surface=default_surface_for_action(action_type),
        risk_class=classify_action_risk(action_type),
        trust_boundary_verdict=item.trust_boundary_verdict,
        opb_verdict=item.opb_verdict,
        raw_payload_ref=f".hg-local/social/drafts/{item.draft_id}.json",
        execution_receipt_ref=item.publish_receipt_ref,
    )
    req.item_hash = req.to_payload()["item_hash"]
    oqi = OperatorQueueItem(queue_item_id=item.queue_item_id, action_request=req)
    oqi.refresh_hash()
    return oqi


def to_social_review_compat(item: OperatorQueueItem) -> dict[str, Any]:
    """Projection for legacy social review consumers — display only."""
    p = item.to_payload()
    return {
        "queue_item_id": item.queue_item_id,
        "draft_id": item.action_id,
        "surface_id": item.requested_surface.value,
        "sanitized_preview": item.sanitized_preview,
        "status": item.status.value,
        "trust_boundary_verdict": p.get("trust_boundary_verdict", "UNKNOWN"),
        "opb_verdict": p.get("opb_verdict", "UNKNOWN"),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def from_social_draft(**kwargs) -> OperatorQueueItem:
    req = _from_social_draft(**kwargs)
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=req)
    item.refresh_hash()
    return item


def from_social_publish_request(**kwargs) -> OperatorQueueItem:
    req = _from_social_publish(**kwargs)
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=req)
    item.refresh_hash()
    return item


def from_exciton_control_request(request: ExcitonControlRequest) -> OperatorQueueItem:
    req = _from_exciton_control(request)
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=req)
    item.refresh_hash()
    return item


def from_tool_request(**kwargs) -> OperatorQueueItem:
    req = _from_tool(**kwargs)
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=req)
    item.refresh_hash()
    return item


def from_anchor_push_request(
    *,
    anchor_ref: str,
    summary: str,
    source_task: str = "",
    source_agent: str = "agent0",
) -> OperatorQueueItem:
    from hg_runtime.exciton_action_model.adapters import _base_request

    req = _base_request(
        AgentActionType.ANCHOR_PUSH,
        source_agent=source_agent,
        source_task=source_task or anchor_ref,
        title="Anchor push request",
        human_summary=summary,
        sanitized_preview=summary[:500],
        raw_payload_ref=f".hg-local/anchor/requests/{anchor_ref}.json",
    )
    item = OperatorQueueItem(queue_item_id=new_queue_item_id(), action_request=req)
    item.refresh_hash()
    return item


__all__ = [
    "from_anchor_push_request",
    "from_exciton_control_request",
    "from_social_draft",
    "from_social_publish_request",
    "from_social_review_item",
    "from_tool_request",
    "to_social_review_compat",
]
