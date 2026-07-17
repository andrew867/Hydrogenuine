"""Tool request broker — governed request path only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from hg_runtime.tool_capability_fabric.organ_access import load_organ_allowlists, organ_may_request, out_of_scope_denial_detail
from hg_runtime.tool_capability_fabric.registry import CapabilityRegistry
from hg_runtime.tool_capability_fabric.tools import execute_local_tool
from hg_runtime.tool_capability_fabric.types import (
    FIXTURE_CLOCK,
    ToolApprovalReceipt,
    ToolDenialReceipt,
    ToolExecutionReceipt,
    ToolRequest,
    advisory_envelope,
)

LOCAL_EXECUTABLE = frozenset(
    {
        "capability_manifest",
        "local_memory_read",
        "proof_read",
        "proof_verify",
        "artifact_read",
        "storage_read",
        "knowledge_lookup",
        "social_draft",
        "email_draft",
        "operator_message",
        "shell_safe",
        "model_inference",
        "web_search_request",
        "browser_read_page",
        "browser_open_url_request",
        "browser_extract_text",
        "browser_screenshot",
        "browser_search_public_web_request",
    }
)

WRITE_REQUEST_ONLY = frozenset({"memory_write_request", "storage_write_request", "artifact_write_request"})
REVIEW_REQUIRED = frozenset(
    {
        "social_publish_request",
        "email_send_request",
        "gmail_send_request",
        "gmail_read_request",
        "account_creation_request",
        "github_write_request",
        "shell_privileged_request",
        "oea_action_request",
        "ter_tool_request",
    }
)
PERMIT_REQUIRED = frozenset({"oea_action_request", "ter_tool_request"})


@dataclass
class BrokerResult:
    state: str
    approval: ToolApprovalReceipt | None = None
    denial: ToolDenialReceipt | None = None
    execution: ToolExecutionReceipt | None = None
    journal_events: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="tool-broker-result",
            state=self.state,
            approval=self.approval.to_payload() if self.approval else None,
            denial=self.denial.to_payload() if self.denial else None,
            execution=self.execution.to_payload() if self.execution else None,
            journal_event_count=len(self.journal_events),
        )


class ToolBroker:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry
        self.journal: list[dict[str, Any]] = []

    def _journal(self, event_type: str, **payload: Any) -> None:
        entry = advisory_envelope(schema="tool-request-journal", event_type=event_type, timestamp=FIXTURE_CLOCK, **payload)
        self.journal.append(entry)

    def submit(self, request: ToolRequest, *, execute_local: bool = True) -> BrokerResult:
        events: list[dict[str, Any]] = []
        self._journal("ToolRequestSubmitted", request=request.to_payload())
        events.append(advisory_envelope(event_type="ToolRequestSubmitted", **request.to_payload()))

        cap = self.registry.get(request.capability_id)
        if cap is None:
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="POLICY_REFUSAL",
                explanation="Unknown capability",
                safe_alternative="request capability_manifest",
                missing_requirement="registered_capability",
            )
            self._journal("ToolDenied", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="ToolDenied", **denial.to_payload()))
            return BrokerResult(state="DENIED", denial=denial, journal_events=events)

        self._journal("ToolPolicyCheckStarted", capability_id=cap.capability_id)
        events.append(advisory_envelope(event_type="ToolPolicyCheckStarted", capability_id=cap.capability_id))

        if not organ_may_request(request.organ_id, request.capability_id):
            detail = out_of_scope_denial_detail(request.organ_id, request.capability_id)
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="ORGAN_SCOPE_DENIED",
                explanation=detail["explanation"],
                safe_alternative=detail["safe_alternative"],
                missing_requirement=detail["missing_requirement"],
            )
            self._journal("ToolCapabilityDeniedByScope", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="ToolCapabilityDeniedByScope", **denial.to_payload()))
            return BrokerResult(state="DENIED", denial=denial, journal_events=events)

        if not cap.enabled:
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="CAPABILITY_DISABLED",
                explanation=f"{cap.name} is disabled by default",
                safe_alternative="use knowledge_lookup or local_memory_read",
                missing_requirement="operator_enable_or_provider_config",
            )
            if cap.requires_oauth_secret:
                denial.missing_requirement = "oauth_secret"
                denial.denial_reason = "OAUTH_SECRET_REQUIRED"
            if cap.external_network_required:
                denial.denial_reason = "EXTERNAL_NETWORK_REQUIRED"
            self._journal("ToolDenied", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="ToolDenied", **denial.to_payload()))
            return BrokerResult(state="DENIED", denial=denial, journal_events=events)

        if request.capability_id in PERMIT_REQUIRED or cap.requires_gpp_permit:
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="PERMIT_REQUIRED",
                explanation="GPP permit required before execution",
                safe_alternative="submit operator_message for permit review",
                missing_requirement="gpp_permit",
                permit_required=True,
                state="PERMIT_REQUIRED",
            )
            self._journal("ToolCapabilityRequiresPermit", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="ToolCapabilityRequiresPermit", **denial.to_payload()))
            return BrokerResult(state="PERMIT_REQUIRED", denial=denial, journal_events=events)

        if request.capability_id in REVIEW_REQUIRED or cap.requires_operator_approval:
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="OPERATOR_REVIEW_REQUIRED",
                explanation="High-risk or publish action requires operator review",
                safe_alternative="use social_draft locally or operator_message",
                missing_requirement="operator_approval",
                operator_required=True,
                state="OPERATOR_REVIEW_REQUIRED",
            )
            self._journal("OperatorReviewRequired", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="OperatorReviewRequired", **denial.to_payload()))
            return BrokerResult(state="OPERATOR_REVIEW_REQUIRED", denial=denial, journal_events=events)

        if cap.live_enabled is False and request.requested_action in ("publish", "send", "delete", "post"):
            denial = ToolDenialReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                denial_reason="LIVE_DISABLED",
                explanation="Live external action disabled",
                safe_alternative="social_draft locally",
                missing_requirement="live_scope_and_operator_approval",
            )
            self._journal("ToolCapabilityLiveDisabled", denial=denial.to_payload())
            events.append(advisory_envelope(event_type="ToolCapabilityLiveDisabled", **denial.to_payload()))
            return BrokerResult(state="DENIED", denial=denial, journal_events=events)

        expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        approval = ToolApprovalReceipt(
            request_id=request.request_id,
            run_id=request.run_id,
            organ_id=request.organ_id,
            capability_id=request.capability_id,
            scope={"read_only": cap.read_only, "draft_only": cap.draft_only, "parameters": request.parameters},
            expires_at=expires,
            rate_limit=cap.max_rate,
            allowed_operation=request.requested_action,
        )
        self._journal("ToolApprovedScoped", approval=approval.to_payload())
        events.append(advisory_envelope(event_type="ToolApprovedScoped", **approval.to_payload()))

        if request.capability_id in WRITE_REQUEST_ONLY:
            exec_receipt = ToolExecutionReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                success=True,
                result_summary="write request recorded; no mutation performed",
                live_side_effect=False,
            )
            self._journal("ToolExecutionCompleted", execution=exec_receipt.to_payload())
            events.append(advisory_envelope(event_type="ToolExecutionCompleted", **exec_receipt.to_payload()))
            return BrokerResult(state="APPROVED_SCOPED", approval=approval, execution=exec_receipt, journal_events=events)

        if execute_local and request.capability_id in LOCAL_EXECUTABLE:
            manifest = self.registry.build_manifest(organ_id=request.organ_id) if request.capability_id == "capability_manifest" else None
            tool_result = execute_local_tool(request.capability_id, request.parameters, manifest=manifest)
            if tool_result.get("denied"):
                denial = ToolDenialReceipt(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    organ_id=request.organ_id,
                    capability_id=request.capability_id,
                    denial_reason="SHELL_NOT_ALLOWLISTED",
                    explanation="Shell command not on allowlist",
                    safe_alternative="git status --short or docker compose ps",
                    missing_requirement="allowlisted_command",
                )
                self._journal("ToolDenied", denial=denial.to_payload())
                return BrokerResult(state="DENIED", denial=denial, approval=approval, journal_events=events)
            exec_receipt = ToolExecutionReceipt(
                request_id=request.request_id,
                run_id=request.run_id,
                organ_id=request.organ_id,
                capability_id=request.capability_id,
                success=bool(tool_result.get("success", True)),
                result_summary=str(tool_result.get("schema", "ok")),
                result_ref=tool_result.get("result_hash") or tool_result.get("draft_hash") or "local",
                live_side_effect=bool(tool_result.get("live_side_effect", False)),
            )
            self._journal("ToolExecutionCompleted", execution=exec_receipt.to_payload())
            events.append(advisory_envelope(event_type="ToolExecutionCompleted", **exec_receipt.to_payload()))
            self._journal("ToolReceiptRecorded", receipt=exec_receipt.to_payload())
            return BrokerResult(state="EXECUTED", approval=approval, execution=exec_receipt, journal_events=events)

        return BrokerResult(state="APPROVED_SCOPED", approval=approval, journal_events=events)


def new_request(
    *,
    run_id: str,
    organ_id: str,
    capability_id: str,
    requested_action: str = "read",
    parameters: dict[str, Any] | None = None,
    agent_id: str = "agent:Agent0",
) -> ToolRequest:
    return ToolRequest(
        request_id=f"tool-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        agent_id=agent_id,
        organ_id=organ_id,
        capability_id=capability_id,
        requested_action=requested_action,
        parameters=parameters or {},
    )


__all__ = ["BrokerResult", "ToolBroker", "new_request"]
