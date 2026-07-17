"""Dry dispatch tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.action_candidate import create_candidate
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.dry_dispatch import execute_dry_dispatch
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import issue_permit, revoke_permit


def _permit(run_id: str):
    c = create_candidate(
        run_id=run_id,
        platform="moltbook",
        action_type="publish_post",
        content="dispatch test",
        scope="platform:moltbook:draft-only",
    )
    req = create_authority_request(
        run_id=run_id,
        candidate_id=c.candidate_id,
        capability_decision_ref=f"broker:create_external_action_candidate:{c.candidate_id}",
    )
    conf = create_dry_operator_confirmation(
        run_id=run_id,
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash=c.content_hash,
    )
    decision = issue_permit(
        run_id=run_id,
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert decision.permit is not None
    return decision.permit


def test_dry_dispatch_requires_permit():
    receipt = execute_dry_dispatch(run_id="no-permit", permit_id="missing")
    assert receipt is None


def test_dry_dispatch_refuses_revoked_permit():
    permit = _permit("revoked-dispatch")
    revoke_permit("revoked-dispatch", permit.permit_id)
    receipt = execute_dry_dispatch(run_id="revoked-dispatch", permit_id=permit.permit_id)
    assert receipt is None


def test_dry_dispatch_external_side_effect_false():
    permit = _permit("dry-success")
    receipt = execute_dry_dispatch(run_id="dry-success", permit_id=permit.permit_id)
    assert receipt is not None
    assert receipt.external_side_effect is False


def test_dry_dispatch_does_not_call_platform_api(monkeypatch):
    called = {"n": 0}

    def _fake_post(*args, **kwargs):
        called["n"] += 1
        return None

    monkeypatch.setattr("urllib.request.urlopen", _fake_post)
    permit = _permit("no-api")
    receipt = execute_dry_dispatch(run_id="no-api", permit_id=permit.permit_id)
    assert receipt is not None
    assert called["n"] == 0
