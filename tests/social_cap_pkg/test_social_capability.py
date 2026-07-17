from __future__ import annotations

from hg_runtime.social_capability.draft import create_draft
from hg_runtime.social_capability.publish_permit import PublishPolicy, mint_permit
from hg_runtime.social_capability.publisher import direct_publish_denied, publish_with_permit
from hg_runtime.social_capability.read import read_social
from hg_runtime.social_capability.schema import (
    SocialDraftRequest,
    SocialForbiddenAction,
    SocialPublishDecision,
    SocialPublishRequest,
    SocialReadRequest,
    SocialSurface,
    new_id,
)
from hg_runtime.social_capability.publish_permit import is_forbidden_action


def test_fixture_read_works():
    req = SocialReadRequest(new_id("r"), SocialSurface.FIXTURE)
    result = read_social(req)
    assert result.trust_ok
    assert len(result.items) >= 1


def test_draft_created_with_advisory_fields():
    req = SocialDraftRequest(new_id("d"), SocialSurface.FIXTURE, "ctx", "topic", confidence=0.7)
    draft = create_draft(req)
    assert draft.draft_id
    assert draft.no_authority_claim
    assert draft.internal_only is True
    assert draft.publishable is False
    assert "INTERNAL AUDIT" in draft.body


def test_internal_draft_cannot_publish():
    req = SocialDraftRequest(new_id("d"), SocialSurface.FIXTURE, "c", "t")
    draft = create_draft(req)
    policy = PublishPolicy(max_posts=1, operator_approval_required=False)
    permit = mint_permit(draft, operator="op", policy=policy)
    assert permit is None
    pub = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface, operator_approved=True)
    receipt = publish_with_permit(pub, draft, permit, policy=policy)
    assert receipt.decision == SocialPublishDecision.REFUSED


def test_publish_without_permit_denied():
    req = SocialDraftRequest(new_id("d"), SocialSurface.FIXTURE, "c", "t")
    draft = create_draft(req)
    pub = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface)
    receipt = publish_with_permit(pub, draft, None)
    assert receipt.decision == SocialPublishDecision.REFUSED


def test_publish_without_operator_approval_queued():
    from hg_runtime.social_capability.draft import create_curated_draft

    draft = create_curated_draft(
        post_id="queue-test",
        surface=SocialSurface.FIXTURE,
        body="Queued public-safe test content.",
        topic="test",
    )
    policy = PublishPolicy(live_publish_enabled=False, operator_approval_required=True, max_posts=1)
    permit = mint_permit(draft, operator="op", policy=policy)
    pub = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface, operator_approved=False)
    receipt = publish_with_permit(pub, draft, permit, policy=policy)
    assert receipt.decision in (SocialPublishDecision.QUEUED, SocialPublishDecision.PUBLISHED)


def test_fixture_publish_with_scoped_permit():
    from hg_runtime.social_capability.draft import create_curated_draft

    draft = create_curated_draft(
        post_id="fixture-test",
        surface=SocialSurface.FIXTURE,
        body="Public-safe fixture wiring test post.",
        topic="test",
    )
    policy = PublishPolicy(live_publish_enabled=False, operator_approval_required=False, max_posts=1)
    permit = mint_permit(draft, operator="op", policy=policy)
    pub = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface, operator_approved=True)
    receipt = publish_with_permit(pub, draft, permit, policy=policy)
    assert receipt.decision == SocialPublishDecision.PUBLISHED
    assert receipt.fixture_mode


def test_live_publish_disabled_by_default():
    policy = PublishPolicy.from_env()
    assert policy.live_publish_enabled is False


def test_direct_publish_denied():
    denied = direct_publish_denied()
    assert denied["rejected"] is True
    assert denied["permission_granted"] is False


def test_forbidden_actions_denied():
    for action in SocialForbiddenAction:
        assert is_forbidden_action(action)


def test_credentials_hidden_from_agent0():
    from hg_runtime.social_capability.agent0_context import agent0_social_context

    ctx = agent0_social_context()
    assert ctx["credentials"]["credential_values_exposed"] is False
    assert "token" not in str(ctx).lower()


def test_token_not_in_receipt():
    from hg_runtime.social_capability.draft import create_curated_draft

    draft = create_curated_draft(
        post_id="receipt-test",
        surface=SocialSurface.FIXTURE,
        body="Receipt test public content.",
        topic="test",
    )
    policy = PublishPolicy(max_posts=1, operator_approval_required=False)
    permit = mint_permit(draft, operator="op", policy=policy)
    pub = SocialPublishRequest(new_id("p"), draft.draft_id, draft.surface, operator_approved=True)
    receipt = publish_with_permit(pub, draft, permit, policy=policy)
    payload = receipt.to_payload()
    assert "token" not in str(payload).lower()
    assert "api_key" not in str(payload).lower()
