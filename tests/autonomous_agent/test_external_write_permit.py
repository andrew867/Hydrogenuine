"""External write permit tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from hg_runtime.external_write_authority.action_candidate import create_candidate, load_candidate, update_candidate_status
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import ExternalWritePermitVerifier, issue_permit, load_permit, revoke_permit
from hg_runtime.external_write_authority.schema import CandidateStatus, PermitDenyReason, PermitStatus


def _fixture_flow(run_id: str, *, capability_ref: str | None = None):
    c = create_candidate(
        run_id=run_id,
        platform="moltbook",
        action_type="publish_post",
        content="permit test",
        scope="platform:moltbook:draft-only",
    )
    ref = capability_ref or f"broker:create_external_action_candidate:{c.candidate_id}"
    req = create_authority_request(run_id=run_id, candidate_id=c.candidate_id, capability_decision_ref=ref)
    conf = create_dry_operator_confirmation(
        run_id=run_id,
        operator_ref="op-fixture",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash=c.content_hash,
    )
    return c, req, conf


def test_permit_requires_candidate():
    decision = issue_permit(
        run_id="missing-cand",
        authority_request_id="nope",
        operator_confirmation_id="nope",
    )
    assert not decision.granted


def test_permit_requires_capability_decision():
    c = create_candidate(
        run_id="cap-miss",
        platform="moltbook",
        action_type="publish_post",
        content="x",
        scope="platform:moltbook:draft-only",
    )
    req = create_authority_request(run_id="cap-miss", candidate_id=c.candidate_id, capability_decision_ref="")
    conf = create_dry_operator_confirmation(
        run_id="cap-miss",
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
        run_id="cap-miss",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert PermitDenyReason.MISSING_CAPABILITY_DECISION in decision.deny_reasons


def test_permit_rejects_stale_candidate():
    c, req, conf = _fixture_flow("stale-cand")
    update_candidate_status("stale-cand", c.candidate_id, CandidateStatus.INVALID)
    decision = issue_permit(
        run_id="stale-cand",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert not decision.granted


def test_permit_rejects_expired_candidate():
    import json
    from pathlib import Path

    c = create_candidate(
        run_id="exp-cand",
        platform="moltbook",
        action_type="publish_post",
        content="x",
        scope="platform:moltbook:draft-only",
        ttl_seconds=3600,
    )
    cand_path = Path(".hg-local/external_write_authority/exp-cand/candidates") / f"{c.candidate_id}.json"
    data = json.loads(cand_path.read_text(encoding="utf-8"))
    data["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    cand_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    cand = load_candidate("exp-cand", c.candidate_id)
    assert cand is not None and cand.is_expired()
    req = create_authority_request(
        run_id="exp-cand",
        candidate_id=c.candidate_id,
        capability_decision_ref=f"broker:create_external_action_candidate:{c.candidate_id}",
    )
    conf = create_dry_operator_confirmation(
        run_id="exp-cand",
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
        run_id="exp-cand",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert PermitDenyReason.EXPIRED_CANDIDATE in decision.deny_reasons


def test_permit_rejects_capability_mismatch():
    c, req, conf = _fixture_flow("cap-mismatch", capability_ref="broker:publish:bad")
    decision = issue_permit(
        run_id="cap-mismatch",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert PermitDenyReason.CAPABILITY_MISMATCH in decision.deny_reasons


def test_permit_rejects_scope_expansion():
    c, req, conf = _fixture_flow("scope-exp")
    conf_bad = create_dry_operator_confirmation(
        run_id="scope-exp",
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform=c.requested_platform,
        action_type=c.requested_action_type.value,
        scope="platform:moltbook:publish-all",
        content_hash=c.content_hash,
    )
    decision = issue_permit(
        run_id="scope-exp",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf_bad.operator_confirmation_id,
    )
    assert not decision.granted


def test_permit_rejects_platform_action_mismatch():
    c, req, _ = _fixture_flow("plat-mismatch")
    conf_bad = create_dry_operator_confirmation(
        run_id="plat-mismatch",
        operator_ref="op",
        candidate_id=c.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"dry-run authorize candidate {c.candidate_id}",
        platform="fourclaw",
        action_type=c.requested_action_type.value,
        scope=c.scope,
        content_hash=c.content_hash,
    )
    decision = issue_permit(
        run_id="plat-mismatch",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf_bad.operator_confirmation_id,
    )
    assert not decision.granted


def test_permit_expires_and_revocation():
    c, req, conf = _fixture_flow("revoke-test")
    decision = issue_permit(
        run_id="revoke-test",
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert decision.granted and decision.permit is not None
    assert decision.permit.dry_run_only is True
    assert decision.permit.live_dispatch_allowed is False
    revoked = revoke_permit("revoke-test", decision.permit.permit_id)
    assert revoked is not None and revoked.status == PermitStatus.REVOKED


def test_permit_cannot_self_mint_from_model_output():
    verifier = ExternalWritePermitVerifier()
    reasons = verifier.verify_capability(capability_decision_ref="model_output:approve publish")
    assert PermitDenyReason.MODEL_OUTPUT_NOT_AUTHORITY in reasons
