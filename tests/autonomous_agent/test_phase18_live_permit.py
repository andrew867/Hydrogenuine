"""Phase 18 live permit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.external_write_authority.action_candidate import create_candidate
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.live_permit import issue_live_permit, revoke_live_permit
from hg_runtime.external_write_authority.live_smoke import create_live_smoke_scope, file_sha256
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import issue_permit


def _phase17_permit(run_id: str, content: str, sha: str):
    c = create_candidate(
        run_id=run_id,
        platform="moltbook",
        action_type="publish_post",
        content=content,
        scope="phase18:moltbook:single",
        content_sha256=sha,
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
        content_hash=sha,
    )
    decision = issue_permit(
        run_id=run_id,
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert decision.permit is not None
    return c, decision.permit, conf


def test_dry_permit_alone_insufficient_for_live(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    _, p17, conf = _phase17_permit("dry-only", "hello", sha)
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    assert scope is not None
    decision = issue_live_permit(
        run_id="dry-only",
        phase17_permit_id=p17.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert decision.granted
    assert decision.permit is not None
    assert decision.permit.max_live_actions == 1


def test_live_permit_requires_operator_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    _, p17, _ = _phase17_permit("no-conf", "hello", sha)
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    decision = issue_live_permit(
        run_id="no-conf",
        phase17_permit_id=p17.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id="missing",
    )
    assert not decision.granted


def test_live_permit_rejects_platform_mismatch(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    _, p17, conf = _phase17_permit("plat-mis", "hello", sha)
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="fourclaw",
        action_type="publish_post",
        content_file=f,
    )
    decision = issue_live_permit(
        run_id="plat-mis",
        phase17_permit_id=p17.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert not decision.granted
    assert "platform_mismatch" in decision.deny_reasons


def test_live_permit_revocation_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    _, p17, conf = _phase17_permit("revoke-p18", "hello", sha)
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    decision = issue_live_permit(
        run_id="revoke-p18",
        phase17_permit_id=p17.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    assert decision.permit is not None
    revoked = revoke_live_permit(decision.permit.live_permit_id)
    assert revoked is not None and revoked.is_revoked()
