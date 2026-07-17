"""Social autopilot policy — evaluate templates at runtime; never global authority."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hg_runtime.social_capability.permit_templates import (
    AllowedActionType,
    SocialOperatorApprovalMode,
    SocialPermitTemplate,
)
from hg_runtime.social_capability.publish_permit import PublishPolicy
from hg_runtime.social_capability.schema import SocialForbiddenAction, _frozen, new_id, social_hash


class SocialAutopilotVerdict(str, Enum):
    ALLOW_DRAFT = "ALLOW_DRAFT"
    ALLOW_QUEUE = "ALLOW_QUEUE"
    ALLOW_READ = "ALLOW_READ"
    QUEUED_FOR_OPERATOR = "QUEUED_FOR_OPERATOR"
    DENIED = "DENIED"
    STOPPED = "STOPPED"
    REFUSED_UNSAFE = "REFUSED_UNSAFE"


@dataclass
class SocialAutopilotPolicy:
    """Default safe policy for Agent Zero bounded soak."""

    templates_enabled: bool = True
    live_read_enabled: bool = True
    draft_enabled: bool = True
    queue_enabled: bool = True
    live_publish_enabled: bool = False
    max_posts_default: int = 0
    first_soak_max_posts: int = 1
    operator_approval_required: bool = True
    global_stop: bool = False
    global_panic: bool = False

    @classmethod
    def from_env(cls) -> "SocialAutopilotPolicy":
        return cls(
            templates_enabled=os.environ.get("HG_SOCIAL_TEMPLATES_ENABLED", "true").lower() in ("1", "true", "yes"),
            live_read_enabled=os.environ.get("HG_SOCIAL_LIVE_READ", "").lower() in ("1", "true", "yes"),
            draft_enabled=True,
            queue_enabled=True,
            live_publish_enabled=os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "").lower() in ("1", "true", "yes"),
            max_posts_default=int(os.environ.get("HG_SOCIAL_MAX_POSTS", "0")),
            operator_approval_required=os.environ.get("HG_SOCIAL_OPERATOR_APPROVAL_REQUIRED", "true").lower()
            in ("1", "true", "yes"),
        )


@dataclass
class SocialAutopilotDecision:
    decision_id: str
    template_id: str
    verdict: SocialAutopilotVerdict
    reason: str
    permit_may_mint: bool
    operator_approval_required: bool
    posts_allowed: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "social-autopilot-decision",
            "decision_id": self.decision_id,
            "template_id": self.template_id,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "permit_may_mint": self.permit_may_mint,
            "operator_approval_required": self.operator_approval_required,
            "posts_allowed": self.posts_allowed,
            **_frozen(),
        }


@dataclass
class SocialAutopilotReceipt:
    receipt_id: str
    template_id: str
    decision_id: str
    created_at: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "social-autopilot-receipt",
            "receipt_id": self.receipt_id,
            "template_id": self.template_id,
            "decision_id": self.decision_id,
            "created_at": self.created_at,
            "detail": self.detail,
            **_frozen(),
        }
        payload["content_hash"] = social_hash(payload)
        return payload


def evaluate_template(
    template: SocialPermitTemplate,
    *,
    policy: SocialAutopilotPolicy | None = None,
    publish_policy: PublishPolicy | None = None,
    action: AllowedActionType | None = None,
    stop_requested: bool = False,
    panic_requested: bool = False,
    posts_used: int = 0,
) -> SocialAutopilotDecision:
    """Evaluate a permit template at runtime. Template cannot approve itself."""
    policy = policy or SocialAutopilotPolicy.from_env()
    publish_policy = publish_policy or PublishPolicy.from_env()
    action = action or template.allowed_action_type
    decision_id = new_id("sad")

    if panic_requested or policy.global_panic:
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.STOPPED,
            "panic stop active", False, True, 0,
        )
    if stop_requested or policy.global_stop:
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.STOPPED,
            "stop requested", False, True, 0,
        )
    if not policy.templates_enabled or not template.enabled:
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.DENIED,
            "templates disabled globally", False, True, 0,
        )
    if action == AllowedActionType.PUBLISH:
        if not publish_policy.live_publish_enabled:
            return SocialAutopilotDecision(
                decision_id, template.template_id, SocialAutopilotVerdict.QUEUED_FOR_OPERATOR,
                "YELLOW_LIVE_SOCIAL_DISABLED", False, True, 0,
            )
        max_posts = min(
            template.rate_limit.max_posts_per_run or policy.first_soak_max_posts,
            policy.first_soak_max_posts,
        )
        if max_posts <= 0 or posts_used >= max_posts:
            return SocialAutopilotDecision(
                decision_id, template.template_id, SocialAutopilotVerdict.DENIED,
                "rate limit: max posts per run", False, True, 0,
            )
        op_required = (
            policy.operator_approval_required
            or template.operator_approval_mode == SocialOperatorApprovalMode.REQUIRED
        )
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.QUEUED_FOR_OPERATOR,
            "publish requires scoped permit + operator approval",
            permit_may_mint=True,
            operator_approval_required=op_required,
            posts_allowed=max(0, max_posts - posts_used),
        )
    if action == AllowedActionType.QUEUE:
        if not policy.queue_enabled:
            return SocialAutopilotDecision(
                decision_id, template.template_id, SocialAutopilotVerdict.DENIED,
                "queue disabled", False, True, 0,
            )
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.ALLOW_QUEUE,
            "queue for operator", False, True, 0,
        )
    if action == AllowedActionType.DRAFT:
        if not policy.draft_enabled:
            return SocialAutopilotDecision(
                decision_id, template.template_id, SocialAutopilotVerdict.DENIED,
                "draft disabled", False, True, 0,
            )
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.ALLOW_DRAFT,
            "draft allowed under template", False, True, 0,
        )
    if action == AllowedActionType.READ:
        if not policy.live_read_enabled:
            return SocialAutopilotDecision(
                decision_id, template.template_id, SocialAutopilotVerdict.ALLOW_READ,
                "fixture/read-only path", False, True, 0,
            )
        return SocialAutopilotDecision(
            decision_id, template.template_id, SocialAutopilotVerdict.ALLOW_READ,
            "read allowed", False, True, 0,
        )
    return SocialAutopilotDecision(
        decision_id, template.template_id, SocialAutopilotVerdict.DENIED,
        "unknown action", False, True, 0,
    )


def is_forbidden_template_action(template: SocialPermitTemplate, action: SocialForbiddenAction) -> bool:
    return action in template.forbidden_actions


def write_autopilot_receipt(decision: SocialAutopilotDecision, *, template_id: str) -> SocialAutopilotReceipt:
    return SocialAutopilotReceipt(
        receipt_id=new_id("sar"),
        template_id=template_id,
        decision_id=decision.decision_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        detail=decision.to_payload(),
    )


__all__ = [
    "SocialAutopilotDecision",
    "SocialAutopilotPolicy",
    "SocialAutopilotReceipt",
    "SocialAutopilotVerdict",
    "evaluate_template",
    "is_forbidden_template_action",
    "write_autopilot_receipt",
]
