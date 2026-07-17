"""Review queue policy — per-item gates, no global permission."""

from __future__ import annotations

from hg_runtime.social_capability.review_schema import SocialReviewItem, SocialReviewStatus


def item_may_publish(item: SocialReviewItem) -> tuple[bool, str]:
    if item.status != SocialReviewStatus.APPROVED:
        return False, f"status={item.status.value} not approved"
    if not item.publish_eligible:
        return False, "publish_eligible=false"
    if not item.approval_handle:
        return False, "missing approval handle"
    return True, "ok"


def item_may_approve(item: SocialReviewItem) -> tuple[bool, str]:
    if item.status != SocialReviewStatus.QUEUED:
        return False, f"cannot approve status={item.status.value}"
    if not item.publish_eligible:
        return False, "not publish eligible"
    return True, "ok"


def item_may_deny(item: SocialReviewItem) -> tuple[bool, str]:
    if item.status != SocialReviewStatus.QUEUED:
        return False, f"cannot deny status={item.status.value}"
    return True, "ok"


def unreviewed_publish_path(
    *,
    publish_enabled: bool,
    live_publish_paused: bool,
    approved_only_mode: bool,
) -> bool:
    """True when publish could bypass per-item review."""
    if live_publish_paused:
        return False
    if publish_enabled and not approved_only_mode:
        return True
    return False


__all__ = ["item_may_approve", "item_may_deny", "item_may_publish", "unreviewed_publish_path"]
