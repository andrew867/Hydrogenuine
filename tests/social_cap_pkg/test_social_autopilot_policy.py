from __future__ import annotations

from hg_runtime.social_capability.autopilot_policy import (
    SocialAutopilotPolicy,
    SocialAutopilotVerdict,
    evaluate_template,
)
from hg_runtime.social_capability.legacy_import import import_legacy_rules
from hg_runtime.social_capability.permit_templates import AllowedActionType
from hg_runtime.social_capability.publish_permit import PublishPolicy


def test_default_policy_publish_disabled():
    policy = SocialAutopilotPolicy.from_env()
    assert policy.live_publish_enabled is False
    assert policy.max_posts_default == 0


def test_draft_and_queue_enabled_by_default():
    policy = SocialAutopilotPolicy()
    assert policy.draft_enabled is True
    assert policy.queue_enabled is True


def test_preapproved_requires_live_flag():
    templates = import_legacy_rules().migrated_templates
    post_template = next((t for t in templates if t.allowed_action_type == AllowedActionType.QUEUE), templates[0])
    decision = evaluate_template(
        post_template,
        policy=SocialAutopilotPolicy(live_publish_enabled=False),
        publish_policy=PublishPolicy(live_publish_enabled=False, operator_approval_required=True),
        action=AllowedActionType.PUBLISH,
    )
    assert decision.verdict == SocialAutopilotVerdict.QUEUED_FOR_OPERATOR


def test_rate_limit_blocks_excess_posts():
    templates = import_legacy_rules().migrated_templates
    t = templates[0]
    policy = SocialAutopilotPolicy(live_publish_enabled=True, first_soak_max_posts=1)
    pub = PublishPolicy(live_publish_enabled=True, max_posts=1, operator_approval_required=False)
    d1 = evaluate_template(t, policy=policy, publish_policy=pub, action=AllowedActionType.PUBLISH, posts_used=0)
    d2 = evaluate_template(t, policy=policy, publish_policy=pub, action=AllowedActionType.PUBLISH, posts_used=1)
    assert d2.verdict == SocialAutopilotVerdict.DENIED
