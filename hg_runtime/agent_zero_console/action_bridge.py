"""Bridge chat proposals to governed queues — never execute."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_console.policy import chat_can_authorize, chat_can_execute, chat_can_publish, chat_can_send
from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.redaction import sha256
from hg_runtime.agent_zero_console.schema import ConsoleRequest, ProposedAction, RequestIntent
from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.schema import AgentActionRequest, AgentActionStatus, AgentActionSurface
from hg_runtime.exciton_action_model.risk import classify_action_risk
from hg_runtime.operator_action_queue.queue import open_default_queue

WORKSPACE = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_proposal(req: ConsoleRequest, *, summary: str) -> ProposedAction:
    proposal = ProposedAction(
        proposal_id=f"prop-{uuid.uuid4().hex[:12]}",
        conversation_id=req.conversation_id,
        intent=req.intent,
        surface=req.policy.surface,
        summary=summary[:500],
        preview_hash=req.text_hash,
    )
    write_receipt(
        event_type="PROPOSAL_CREATED",
        conversation_id=req.conversation_id,
        payload=proposal.to_dict(),
    )
    return proposal


def handoff_to_operator_queue(req: ConsoleRequest, *, title: str, summary: str) -> dict[str, Any]:
    assert not chat_can_execute(req.intent)
    assert not chat_can_authorize(req.intent)
    assert not chat_can_publish(req.intent)
    assert not chat_can_send(req.intent)

    action_type = AgentActionType.OPERATOR_NOTE
    if req.intent == RequestIntent.CREATE_SOCIAL_DRAFT:
        action_type = AgentActionType.SOCIAL_POST
    elif req.intent == RequestIntent.REQUEST_OPERATOR_REVIEW:
        action_type = AgentActionType.TOOL_EXECUTE

    action = AgentActionRequest(
        action_id=f"act-{uuid.uuid4().hex[:12]}",
        action_type=action_type,
        source_agent="agent_zero_console",
        source_task=req.conversation_id,
        created_at=_now(),
        priority=0,
        status=AgentActionStatus.QUEUED,
        title=title[:200],
        human_summary=summary[:1000],
        sanitized_preview=summary[:500],
        requested_surface=AgentActionSurface.OPERATOR,
        risk_class=classify_action_risk(action_type),
        trust_boundary_verdict="cargo",
    )
    runtime = open_default_queue(WORKSPACE)
    item = runtime.enqueue(action)
    write_receipt(
        event_type="QUEUE_HANDOFF_CREATED",
        conversation_id=req.conversation_id,
        payload={
            "queue_item_id": item.queue_item_id,
            "action_id": item.action_id,
            "intent": req.intent.value,
        },
    )
    return {
        "ok": True,
        "queue_item_id": item.queue_item_id,
        "authority_created": False,
        "permission_granted": False,
    }


def process_request(req: ConsoleRequest) -> dict[str, Any]:
    if req.intent == RequestIntent.STATUS_SYNTHESIS:
        from hg_runtime.agent_zero_console.status_synthesis import answer_how_are_you

        return {"mode": "status", "text": answer_how_are_you(conversation_id=req.conversation_id)}
    if req.intent == RequestIntent.FORBIDDEN:
        return {"mode": "deny", "reason": req.policy.reason}
    if req.intent == RequestIntent.FUTURE_PHASE_REQUIRED:
        return {"mode": "future", "reason": req.policy.reason}
    if req.policy.queue_handoff:
        proposal = create_proposal(req, summary=req.policy.reason)
        handoff = handoff_to_operator_queue(req, title=req.intent.value, summary=req.policy.reason)
        proposal.queue_item_ref = handoff.get("queue_item_id")
        return {"mode": "queue", "proposal": proposal.to_dict(), "handoff": handoff}
    proposal = create_proposal(req, summary=req.policy.reason)
    return {"mode": "answer", "proposal": proposal.to_dict()}


__all__ = ["create_proposal", "handoff_to_operator_queue", "process_request"]
