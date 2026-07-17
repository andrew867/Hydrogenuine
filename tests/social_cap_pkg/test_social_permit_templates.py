from __future__ import annotations

from hg_runtime.social_capability.autopilot_policy import (
    SocialAutopilotPolicy,
    SocialAutopilotVerdict,
    evaluate_template,
    is_forbidden_template_action,
)
from hg_runtime.social_capability.legacy_import import import_legacy_rules
from hg_runtime.social_capability.permit_templates import AllowedActionType
from hg_runtime.social_capability.publish_permit import PublishPolicy
from hg_runtime.social_capability.schema import SocialForbiddenAction


def _first_template():
    templates = import_legacy_rules().migrated_templates
    assert templates
    return templates[0]


def test_template_cannot_publish_without_runtime_permit():
    t = _first_template()
    policy = SocialAutopilotPolicy(live_publish_enabled=False, max_posts_default=0)
    decision = evaluate_template(
        t, policy=policy, publish_policy=PublishPolicy(live_publish_enabled=False),
        action=AllowedActionType.PUBLISH,
    )
    assert decision.verdict in (SocialAutopilotVerdict.QUEUED_FOR_OPERATOR, SocialAutopilotVerdict.DENIED)
    assert decision.permit_may_mint is False or decision.operator_approval_required


def test_template_cannot_bypass_operator_approval_by_default():
    t = _first_template()
    decision = evaluate_template(t, action=AllowedActionType.QUEUE)
    assert decision.operator_approval_required is True


def test_template_cannot_dm_reply_follow_delete():
    t = _first_template()
    for action in (
        SocialForbiddenAction.DM,
        SocialForbiddenAction.REPLY,
        SocialForbiddenAction.FOLLOW,
        SocialForbiddenAction.DELETE,
    ):
        assert is_forbidden_template_action(t, action)


def test_stop_panic_blocks_template():
    t = _first_template()
    stop = evaluate_template(t, stop_requested=True)
    panic = evaluate_template(t, panic_requested=True)
    assert stop.verdict == SocialAutopilotVerdict.STOPPED
    assert panic.verdict == SocialAutopilotVerdict.STOPPED


def test_no_global_permission_granted():
    t = _first_template()
    for action in AllowedActionType:
        d = evaluate_template(t, action=action)
        assert d.to_payload()["permission_granted"] is False
        assert d.to_payload()["authority_created"] is False
