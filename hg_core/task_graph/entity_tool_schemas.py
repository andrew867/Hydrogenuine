"""
JSON contracts for entity tool invocation and approval payloads (Social Media Entity Tools).
Used by tools invoke-plan API, approval service, and social adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---- Tool invocation intent (invoke-plan request/response) ----


@dataclass
class ProposedStep:
    """A single proposed step in an entity tool plan."""
    step_id: str
    tool_id: str
    description: str
    requires_approval: bool = False
    inputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInvocationIntent:
    """Input for tools invoke-plan: entity, request, context, and optional existing steps."""
    entity_id: str
    user_request: str
    context: Dict[str, Any] = field(default_factory=dict)
    proposed_steps: List[ProposedStep] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)  # step_ids requiring approval
    selected_tools: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "user_request": self.user_request,
            "context": self.context,
            "proposed_steps": [
                {
                    "step_id": s.step_id,
                    "tool_id": s.tool_id,
                    "description": s.description,
                    "requires_approval": s.requires_approval,
                    "inputs": s.inputs,
                }
                for s in self.proposed_steps
            ],
            "required_approvals": self.required_approvals,
            "selected_tools": self.selected_tools,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolInvocationIntent":
        steps = [
            ProposedStep(
                step_id=s["step_id"],
                tool_id=s["tool_id"],
                description=s["description"],
                requires_approval=s.get("requires_approval", False),
                inputs=s.get("inputs") or {},
            )
            for s in d.get("proposed_steps") or []
        ]
        return cls(
            entity_id=d["entity_id"],
            user_request=d["user_request"],
            context=d.get("context") or {},
            proposed_steps=steps,
            required_approvals=d.get("required_approvals") or [],
            selected_tools=d.get("selected_tools") or [],
        )


# ---- Approval request payload (preview_json shape) ----


@dataclass
class ApprovalRequestPreview:
    """Shape of preview_json for approval_requests (platform, account, action, draft, artifacts)."""
    platform: str
    account_id: str
    action_type: str
    summary: str
    draft_text: str
    artifact_set_id: str
    target_context: Optional[Dict[str, Any]] = None
    risk_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "account_id": self.account_id,
            "action_type": self.action_type,
            "summary": self.summary,
            "draft_text": self.draft_text,
            "artifact_set_id": self.artifact_set_id,
            "target_context": self.target_context or {},
            "risk_flags": self.risk_flags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ApprovalRequestPreview":
        return cls(
            platform=d["platform"],
            account_id=d["account_id"],
            action_type=d["action_type"],
            summary=d["summary"],
            draft_text=d["draft_text"],
            artifact_set_id=d["artifact_set_id"],
            target_context=d.get("target_context"),
            risk_flags=d.get("risk_flags") or [],
        )


# ---- Approval decision (approve / reject / request_edit) ----


@dataclass
class ApprovalDecision:
    """Decision payload for approving, rejecting, or requesting edit on an approval request."""
    action: str  # "approve" | "reject" | "request_edit"
    note: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "note": self.note,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ApprovalDecision":
        return cls(
            action=d["action"],
            note=d.get("note"),
            reason=d.get("reason"),
        )
