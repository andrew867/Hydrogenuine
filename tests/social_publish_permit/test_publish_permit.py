from __future__ import annotations

from hg_runtime.social_capability.draft import create_curated_draft
from hg_runtime.social_capability.publish_permit import PublishPolicy, evaluate_publish, mint_permit
from hg_runtime.social_capability.schema import SocialPublishRequest, SocialSurface, new_id


def test_scoped_permit_not_global_permission():
    draft = create_curated_draft(
        post_id="permit-test",
        surface=SocialSurface.FIXTURE,
        body="Scoped permit wiring test.",
        topic="test",
    )
    permit = mint_permit(draft, operator="op", policy=PublishPolicy(max_posts=1))
    assert permit is not None
    payload = permit.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_rate_limit_blocks_spam():
    policy = PublishPolicy(max_posts=1, rate_limit_per_hour=1)
    draft = create_curated_draft(
        post_id="rate-test",
        surface=SocialSurface.FIXTURE,
        body="Rate limit wiring test.",
        topic="test",
    )
    permit = mint_permit(draft, operator="op", policy=policy)
    req = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface, operator_approved=True)
    d1, _ = evaluate_publish(req, draft, permit, policy=policy, posts_used=0)
    d2, _ = evaluate_publish(req, draft, permit, policy=policy, posts_used=1)
    assert d2.value == "REFUSED"
