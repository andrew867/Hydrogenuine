"""Social permit templates — legacy cron rules become scoped templates, not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.social_capability.schema import (
    FIXTURE_UTC,
    SocialForbiddenAction,
    SocialSurface,
    _frozen,
    social_hash,
)


class AllowedActionType(str, Enum):
    READ = "read"
    DRAFT = "draft"
    QUEUE = "queue"
    PUBLISH = "publish"


class SocialOperatorApprovalMode(str, Enum):
    REQUIRED = "required"
    PREAPPROVED_SCOPED = "preapproved_scoped"  # only when live publish explicitly enabled
    NEVER = "never"


class MigrationClass(str, Enum):
    MIGRATE_NOW_SAFE = "MIGRATE_NOW_SAFE"
    MIGRATE_WITH_RESTRICTIONS = "MIGRATE_WITH_RESTRICTIONS"
    KEEP_DRY_RUN_ONLY = "KEEP_DRY_RUN_ONLY"
    FUTURE_WORK = "FUTURE_WORK"
    DO_NOT_MIGRATE_UNSAFE = "DO_NOT_MIGRATE_UNSAFE"
    DUPLICATE_OR_SUPERSEDED = "DUPLICATE_OR_SUPERSEDED"
    STALE_INVALID = "STALE_INVALID"


@dataclass
class SocialRateLimit:
    max_posts_per_run: int = 0
    max_posts_per_hour: int = 1
    min_seconds_between_posts: int = 900

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_posts_per_run": self.max_posts_per_run,
            "max_posts_per_hour": self.max_posts_per_hour,
            "min_seconds_between_posts": self.min_seconds_between_posts,
        }


@dataclass
class SocialContentPolicy:
    allowed_topics: tuple[str, ...] = ()
    forbidden_topics: tuple[str, ...] = (
        "authority_claim",
        "personhood",
        "coercion",
        "operator_pressure",
        "private_content",
    )

    def to_payload(self) -> dict[str, Any]:
        return {
            "allowed_topics": list(self.allowed_topics),
            "forbidden_topics": list(self.forbidden_topics),
        }


@dataclass
class SocialPermitTemplate:
    template_id: str
    source_legacy_rule_ref: str
    surface_id: SocialSurface
    allowed_action_type: AllowedActionType
    publish_allowed_default: bool = False
    operator_approval_mode: SocialOperatorApprovalMode = SocialOperatorApprovalMode.REQUIRED
    rate_limit: SocialRateLimit = field(default_factory=SocialRateLimit)
    content_policy: SocialContentPolicy = field(default_factory=SocialContentPolicy)
    forbidden_actions: tuple[SocialForbiddenAction, ...] = field(
        default_factory=lambda: (
            SocialForbiddenAction.DM,
            SocialForbiddenAction.REPLY,
            SocialForbiddenAction.FOLLOW,
            SocialForbiddenAction.UNFOLLOW,
            SocialForbiddenAction.DELETE,
            SocialForbiddenAction.DIRECT_PUBLISH,
        )
    )
    trust_boundary_required: bool = True
    opb_required: bool = True
    permit_required: bool = True
    ewj_receipt_required: bool = True
    stop_panic_required: bool = True
    enabled: bool = True
    migration_class: MigrationClass = MigrationClass.MIGRATE_WITH_RESTRICTIONS
    created_at: str = FIXTURE_UTC
    legacy_interval_minutes: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "social-permit-template",
            "template_id": self.template_id,
            "source_legacy_rule_ref": self.source_legacy_rule_ref,
            "surface_id": self.surface_id.value,
            "allowed_action_type": self.allowed_action_type.value,
            "publish_allowed_default": self.publish_allowed_default,
            "operator_approval_mode": self.operator_approval_mode.value,
            "rate_limit": self.rate_limit.to_payload(),
            "content_policy": self.content_policy.to_payload(),
            "forbidden_actions": [a.value for a in self.forbidden_actions],
            "trust_boundary_required": self.trust_boundary_required,
            "opb_required": self.opb_required,
            "permit_required": self.permit_required,
            "ewj_receipt_required": self.ewj_receipt_required,
            "stop_panic_required": self.stop_panic_required,
            "enabled": self.enabled,
            "migration_class": self.migration_class.value,
            "created_at": self.created_at,
            "legacy_interval_minutes": self.legacy_interval_minutes,
            **_frozen(),
        }
        payload["template_hash"] = template_hash(payload)
        return payload


def template_hash(payload: dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k not in ("template_hash", "content_hash")}
    return social_hash(clean)


__all__ = [
    "AllowedActionType",
    "MigrationClass",
    "SocialContentPolicy",
    "SocialOperatorApprovalMode",
    "SocialPermitTemplate",
    "SocialRateLimit",
    "template_hash",
]
