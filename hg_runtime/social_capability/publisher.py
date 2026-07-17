"""Social publisher — publish only with scoped permit, never direct."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.social_capability.publish_permit import PublishPolicy, evaluate_publish, is_forbidden_action
from hg_runtime.social_capability.receipts import write_publish_receipt
from hg_runtime.social_capability.visibility_contract import build_visibility_contract
from hg_runtime.social_capability.schema import (
    SocialDraft,
    SocialForbiddenAction,
    SocialPublishDecision,
    SocialPublishPermit,
    SocialPublishReceipt,
    SocialPublishRequest,
    SocialSurface,
    new_id,
)

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE_PUBLISH_DIR = WORKSPACE / ".hg-local" / "social" / "fixture_posts"


def deny_forbidden(action: SocialForbiddenAction) -> dict:
    return {
        "rejected": True,
        "code": f"RED_{action.value.upper()}_ENABLED",
        "action": action.value,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def publish_with_permit(
    request: SocialPublishRequest,
    draft: SocialDraft,
    permit: SocialPublishPermit | None,
    *,
    policy: PublishPolicy | None = None,
    posts_used: int = 0,
) -> SocialPublishReceipt:
    for action in SocialForbiddenAction:
        if action == SocialForbiddenAction.DIRECT_PUBLISH:
            continue
        if is_forbidden_action(action):
            pass  # all forbidden by default — no enable path

    decision, reason = evaluate_publish(request, draft, permit, policy=policy, posts_used=posts_used)
    fixture_mode = draft.surface in (SocialSurface.FIXTURE, SocialSurface.LOCAL_TEXT)
    published = decision == SocialPublishDecision.PUBLISHED

    if published and fixture_mode:
        FIXTURE_PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        out = FIXTURE_PUBLISH_DIR / f"{draft.draft_id}.txt"
        out.write_text(draft.body, encoding="utf-8")

    receipt = SocialPublishReceipt(
        receipt_id=new_id("spr"),
        permit_id=permit.permit_id if permit else "none",
        draft_id=draft.draft_id,
        surface=draft.surface,
        decision=decision,
        published=published,
        fixture_mode=fixture_mode,
        created_at=datetime.now(timezone.utc).isoformat(),
        external_visibility=build_visibility_contract(
            surface=draft.surface,
            published=published,
            fixture_mode=fixture_mode,
            permit_id=permit.permit_id if permit else None,
        ),
    )
    write_publish_receipt(receipt, detail={"reason": reason})
    return receipt


def direct_publish_denied() -> dict:
    return deny_forbidden(SocialForbiddenAction.DIRECT_PUBLISH) | {
        "code": "RED_UNAPPROVED_SOCIAL_POST",
        "reason": "direct publish forbidden; require scoped SocialPublishPermit",
    }


__all__ = ["deny_forbidden", "direct_publish_denied", "publish_with_permit"]
