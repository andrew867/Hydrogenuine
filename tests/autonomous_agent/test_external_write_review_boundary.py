"""Review queue is not write approval."""
from __future__ import annotations

from hg_runtime.external_write_authority.action_candidate import create_candidate
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import issue_permit
from hg_runtime.external_write_authority.schema import load_policy
from hg_runtime.operator_review.schema import FORBIDDEN_REVIEW_ACTIONS, ReviewAction


def test_review_queue_decision_is_not_permit():
    policy = load_policy()
    assert policy.get("review_queue_is_approval") is False


def test_forbidden_review_actions_include_publish():
    assert ReviewAction.PUBLISH in FORBIDDEN_REVIEW_ACTIONS
    assert ReviewAction.APPROVE_FOR_PUBLISH in FORBIDDEN_REVIEW_ACTIONS


def test_review_decision_ref_alone_does_not_grant_permit():
    c = create_candidate(
        run_id="review-not-approval",
        platform="moltbook",
        action_type="publish_post",
        content="review",
        scope="platform:moltbook:draft-only",
    )
    req = create_authority_request(
        run_id="review-not-approval",
        candidate_id=c.candidate_id,
        capability_decision_ref=f"broker:create_external_action_candidate:{c.candidate_id}",
        review_decision_ref="review-decision-approve-123",
    )
    decision = issue_permit(
        run_id="review-not-approval",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id="missing",
    )
    assert not decision.granted
