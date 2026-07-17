"""Broker integration for external write authority."""
from __future__ import annotations

from hg_runtime.capability_broker.action_registry import get_action, is_forbidden_action, is_known_action
from hg_runtime.external_write_authority.broker_integration import (
    broker_may_create_candidate,
    create_candidate_from_broker_admission,
)


def test_broker_refuses_direct_publish_send_reply_comment():
    for action in ("publish", "send", "reply_live", "comment_live", "browser_submit"):
        assert is_forbidden_action(action)


def test_broker_may_admit_create_external_action_candidate():
    assert is_known_action("create_external_action_candidate")
    action = get_action("create_external_action_candidate")
    assert action is not None
    assert action.internal_only is True
    assert action.external_side_effect is False
    assert broker_may_create_candidate("create_external_action_candidate")


def test_create_candidate_from_broker_admission():
    c = create_candidate_from_broker_admission(
        run_id="broker-int",
        platform="moltbook",
        action_type="publish_post",
        content="broker path",
        scope="platform:moltbook:draft-only",
        capability_decision_ref="broker:create_external_action_candidate:test",
    )
    assert c.candidate_id


def test_model_output_cannot_authorize_broker_path():
    import pytest

    with pytest.raises(PermissionError):
        create_candidate_from_broker_admission(
            run_id="model-bypass",
            platform="moltbook",
            action_type="publish_post",
            content="x",
            scope="platform:moltbook:draft-only",
            capability_decision_ref="model_output:publish now",
        )
