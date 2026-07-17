"""Social publish permit — scoped authority object, never global permission."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from hg_runtime.social_capability.content_policy import publish_block_reason
from hg_runtime.social_capability.schema import (
    SocialDraft,
    SocialForbiddenAction,
    SocialPublishDecision,
    SocialPublishPermit,
    SocialPublishRequest,
    SocialSurface,
    _frozen,
    new_id,
)

FORBIDDEN_ACTIONS = frozenset(SocialForbiddenAction)


@dataclass
class PublishPolicy:
    live_publish_enabled: bool = False
    operator_approval_required: bool = True
    max_posts: int = 0
    rate_limit_per_hour: int = 3

    @classmethod
    def from_env(cls) -> "PublishPolicy":
        return cls(
            live_publish_enabled=os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "").lower() in ("1", "true", "yes"),
            operator_approval_required=os.environ.get("HG_SOCIAL_OPERATOR_APPROVAL_REQUIRED", "true").lower()
            in ("1", "true", "yes"),
            max_posts=int(os.environ.get("HG_SOCIAL_MAX_POSTS", "0")),
            rate_limit_per_hour=int(os.environ.get("HG_SOCIAL_RATE_LIMIT_PER_HOUR", "3")),
        )


class PublishRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, list[datetime]] = {}

    def allow(self, scope: str, limit: int) -> bool:
        now = datetime.now(timezone.utc)
        window = [t for t in self._counts.get(scope, []) if now - t < timedelta(hours=1)]
        if len(window) >= limit:
            self._counts[scope] = window
            return False
        window.append(now)
        self._counts[scope] = window
        return True


_RATE_LIMITER = PublishRateLimiter()


def is_forbidden_action(action: SocialForbiddenAction) -> bool:
    return action in FORBIDDEN_ACTIONS


def mint_permit(
    draft: SocialDraft,
    *,
    operator: str,
    policy: PublishPolicy | None = None,
    scope: str = "fixture-publish",
    ttl_minutes: int = 30,
) -> SocialPublishPermit | None:
    policy = policy or PublishPolicy.from_env()
    if not draft.trust_ok or not draft.opb_ok:
        return None
    if draft.internal_only or not draft.publishable:
        return None
    blocked = publish_block_reason(draft.body, topic=draft.topic, internal_only=draft.internal_only)
    if blocked:
        return None
    if not draft.no_authority_claim or not draft.no_personhood_claim or not draft.no_coercion:
        return None
    expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    return SocialPublishPermit(
        permit_id=new_id("permit"),
        draft_id=draft.draft_id,
        surface=draft.surface,
        scope=scope,
        max_posts=max(1, policy.max_posts) if policy.max_posts else 1,
        expires_at=expires.isoformat(),
        operator=operator,
        live_publish_enabled=policy.live_publish_enabled,
    )


def evaluate_publish(
    request: SocialPublishRequest,
    draft: SocialDraft,
    permit: SocialPublishPermit | None,
    *,
    policy: PublishPolicy | None = None,
    posts_used: int = 0,
) -> tuple[SocialPublishDecision, str]:
    policy = policy or PublishPolicy.from_env()

    blocked = publish_block_reason(draft.body, topic=draft.topic, internal_only=draft.internal_only)
    if blocked:
        return SocialPublishDecision.REFUSED, blocked

    if draft.internal_only or not draft.publishable:
        return SocialPublishDecision.REFUSED, "RED_INTERNAL_DRAFT_NOT_PUBLISHABLE"

    if permit is None:
        return SocialPublishDecision.REFUSED, "RED_UNAPPROVED_SOCIAL_POST: no permit"

    if permit.draft_id != draft.draft_id:
        return SocialPublishDecision.REFUSED, "permit draft mismatch"

    if policy.operator_approval_required and not request.operator_approved:
        return SocialPublishDecision.QUEUED, "YELLOW_PUBLISH_REQUIRES_OPERATOR"

    if not policy.live_publish_enabled and draft.surface not in (
        SocialSurface.FIXTURE,
        SocialSurface.LOCAL_TEXT,
    ):
        return SocialPublishDecision.QUEUED, "YELLOW_LIVE_SOCIAL_DISABLED"

    if posts_used >= permit.max_posts:
        return SocialPublishDecision.REFUSED, "rate limit: max posts exceeded"

    if not _RATE_LIMITER.allow(permit.scope, policy.rate_limit_per_hour):
        return SocialPublishDecision.REFUSED, "rate limit exceeded"

    try:
        expires = datetime.fromisoformat(permit.expires_at)
        if datetime.now(timezone.utc) > expires:
            return SocialPublishDecision.REFUSED, "permit expired"
    except ValueError:
        return SocialPublishDecision.REFUSED, "invalid permit expiry"

    if draft.surface in (SocialSurface.FIXTURE, SocialSurface.LOCAL_TEXT):
        if not draft.publishable:
            return SocialPublishDecision.REFUSED, "RED_FIXTURE_INTERNAL_DRAFT"
        return SocialPublishDecision.PUBLISHED, "fixture publish with scoped permit"

    if policy.live_publish_enabled and request.operator_approved:
        return SocialPublishDecision.PUBLISHED, "live publish with operator approval and permit"

    return SocialPublishDecision.QUEUED, "queued for operator"


def permit_payload_summary(permit: SocialPublishPermit) -> dict[str, Any]:
    p = permit.to_payload()
    assert "token" not in str(p).lower()
    return p


__all__ = [
    "FORBIDDEN_ACTIONS",
    "PublishPolicy",
    "PublishRateLimiter",
    "evaluate_publish",
    "is_forbidden_action",
    "mint_permit",
    "permit_payload_summary",
]
