"""Operator external write confirmation tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from hg_runtime.external_write_authority.action_candidate import create_candidate
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.operator_confirmation import (
    create_dry_operator_confirmation,
    phrase_is_approve_all,
)


def _base(run_id: str):
    c = create_candidate(
        run_id=run_id,
        platform="moltbook",
        action_type="publish_post",
        content="confirm test",
        scope="platform:moltbook:draft-only",
    )
    req = create_authority_request(
        run_id=run_id,
        candidate_id=c.candidate_id,
        capability_decision_ref=f"broker:create_external_action_candidate:{c.candidate_id}",
    )
    return c, req


def test_operator_confirmation_separate_from_review():
    c, req = _base("review-sep")
    conf = create_dry_operator_confirmation(
        run_id="review-sep",
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash=c.content_hash,
    )
    assert conf.fixture is True
    assert req.review_decision_ref is None


def test_stale_operator_confirmation_rejected():
    c, req = _base("stale-conf")
    conf = create_dry_operator_confirmation(
        run_id="stale-conf",
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash=c.content_hash,
    )
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert conf.is_expired(at=future)


def test_content_hash_mismatch_rejected():
    from hg_runtime.external_write_authority.permit import issue_permit

    c, req = _base("hash-mismatch")
    conf = create_dry_operator_confirmation(
        run_id="hash-mismatch",
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash="deadbeef",
    )
    decision = issue_permit(
        run_id="hash-mismatch",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert not decision.granted


def test_approve_all_phrase_rejected():
    assert phrase_is_approve_all("approve all")
    with pytest.raises(ValueError):
        c, req = _base("approve-all")
        create_dry_operator_confirmation(
            run_id="approve-all",
            operator_ref="op",
            candidate_id=c.candidate_id,
            authority_request_id=req.authority_request_id,
            phrase="approve all",
            platform=c.requested_platform,
            action_type=c.requested_action_type.value,
            scope=c.scope,
            content_hash=c.content_hash,
        )
