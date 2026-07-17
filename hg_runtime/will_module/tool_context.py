"""WILL + Tool Capability Fabric integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.tool_capability_fabric.broker import BrokerResult, ToolBroker, new_request
from hg_runtime.tool_capability_fabric.types import ToolRequest, advisory_envelope
from hg_runtime.will_module.context import WillContext
from hg_runtime.will_module.policy import attempt_will_approval, will_may_contextualize_tool
from hg_runtime.will_module.receipts import WillTrace
from hg_runtime.will_module.schema import SocialPublicationIntent, ToolRequestIntent


@dataclass
class ToolRequestContext:
    request: ToolRequest
    will_context: WillContext | None = None
    will_explanation: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = advisory_envelope(
            schema="tool-request-context",
            request=self.request.to_payload(),
            will_explanation=self.will_explanation,
            will_id=self.will_context.envelope.will_id if self.will_context else None,
            will_hash=self.will_context.envelope.hash if self.will_context else None,
            will_approved_request=False,
        )
        return payload


def attach_will_to_tool_request(request: ToolRequest, will_context: WillContext | None) -> ToolRequestContext:
    explanation = ""
    if will_context:
        if not will_may_contextualize_tool(will_context.envelope):
            explanation = "WILL veto/expiry suggests pause; broker still decides"
        else:
            explanation = f"WILL intent context: {will_context.envelope.intent_summary[:120]}"
    return ToolRequestContext(request=request, will_context=will_context, will_explanation=explanation)


def submit_with_will_context(
    broker: ToolBroker,
    ctx: ToolRequestContext,
    *,
    execute_local: bool = True,
) -> BrokerResult:
    if ctx.will_context:
        trace = ctx.will_context.trace or WillTrace(run_id=ctx.request.run_id, will_id=ctx.will_context.envelope.will_id)
        trace.append(
            "WILL_TOOL_REQUEST_CONTEXT_ATTACHED",
            capability_id=ctx.request.capability_id,
            explanation=ctx.will_explanation,
        )
    approval_attempt = attempt_will_approval(ctx.request.capability_id)
    if approval_attempt.get("rejected"):
        return BrokerResult(
            state="DENIED",
            journal_events=[advisory_envelope(event_type="WILL_AUTHORITY_CONVERSION_REJECTED", **approval_attempt)],
        )
    return broker.submit(ctx.request, execute_local=execute_local)


def social_intent_to_request(
    intent: SocialPublicationIntent,
    *,
    run_id: str,
    organ_id: str = "organ:Agent0",
    will_context: WillContext | None = None,
) -> ToolRequestContext:
    request = new_request(
        run_id=run_id,
        organ_id=organ_id,
        capability_id="social_publish_request",
        requested_action="publish",
        parameters={"channel": intent.channel, "purpose": intent.purpose, "draft_ref": intent.draft_ref},
    )
    request.intent = f"will-social-intent:{intent.purpose}"
    return attach_will_to_tool_request(request, will_context)


def tool_intent_to_request(
    intent: ToolRequestIntent,
    *,
    run_id: str,
    capability_id: str,
    organ_id: str = "organ:Agent0",
    will_context: WillContext | None = None,
) -> ToolRequestContext:
    request = new_request(
        run_id=run_id,
        organ_id=organ_id,
        capability_id=capability_id,
        requested_action="read",
        parameters={"purpose": intent.purpose, "scope_ref": intent.scope_ref},
    )
    request.intent = f"will-tool-intent:{intent.tool_class}"
    return attach_will_to_tool_request(request, will_context)


__all__ = [
    "ToolRequestContext",
    "attach_will_to_tool_request",
    "social_intent_to_request",
    "submit_with_will_context",
    "tool_intent_to_request",
]
