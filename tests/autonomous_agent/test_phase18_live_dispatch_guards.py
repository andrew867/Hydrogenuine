"""Phase 18 live dispatch guard tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_runtime.external_write_authority.action_candidate import create_candidate
from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.incident_plan import create_incident_plan
from hg_runtime.external_write_authority.live_permit import issue_live_permit
from hg_runtime.external_write_authority.live_smoke import create_live_smoke_scope, file_sha256, reset_live_dispatch_count
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import issue_permit
from hg_runtime.external_write_authority.platform_proof import dispatch_live


def _full_chain(run_id: str, f: Path, sha: str):
    c = create_candidate(
        run_id=run_id,
        platform="moltbook",
        action_type="publish_post",
        content=f.read_text(encoding="utf-8"),
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
    p17 = issue_permit(
        run_id=run_id,
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    ).permit
    scope = create_live_smoke_scope(
        operator_ref="op",
        platform="moltbook",
        action_type="publish_post",
        content_file=f,
    )
    live = issue_live_permit(
        run_id=run_id,
        phase17_permit_id=p17.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    ).permit
    create_incident_plan(
        scope_ref=scope.scope_id,
        candidate_ref=c.candidate_id,
        platform="moltbook",
        action_type="publish_post",
    )
    return live


def test_dispatch_live_refuses_by_default(tmp_path, monkeypatch):
    reset_live_dispatch_count()
    monkeypatch.delenv("HG_PHASE18_ALLOW_LIVE_SMOKE", raising=False)
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    live = _full_chain("refuse-default", f, sha)
    monkeypatch.delenv("HG_PHASE18_ALLOW_LIVE_SMOKE", raising=False)
    result, deny = dispatch_live(live_permit_id=live.live_permit_id)
    assert result is None
    assert any("PHASE18" in d or "ENV" in d for d in deny)


def test_missing_incident_plan_blocks_dispatch(tmp_path, monkeypatch):
    reset_live_dispatch_count()
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "true")
    monkeypatch.setenv("HG_PHASE18_USE_FAKE_ADAPTER", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    live = _full_chain("no-incident", f, sha)
    # remove incident plan files
    from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT

    plans = PHASE18_ROOT / "incident_plans"
    for p in plans.glob("*.json"):
        p.unlink()
    result, deny = dispatch_live(live_permit_id=live.live_permit_id)
    assert result is None
    assert "RED_INCIDENT_ROLLBACK_PLAN_MISSING" in deny


def test_stop_blocks_dispatch(tmp_path, monkeypatch):
    reset_live_dispatch_count()
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    monkeypatch.setenv("HG_STOP_ACTIVE", "true")
    monkeypatch.setenv("HG_PHASE18_USE_FAKE_ADAPTER", "true")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    live = _full_chain("stop-block", f, sha)
    result, deny = dispatch_live(live_permit_id=live.live_permit_id)
    assert result is None
    assert "stop_panic_active" in deny


def test_fake_adapter_not_live_green(tmp_path, monkeypatch):
    reset_live_dispatch_count()
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "true")
    monkeypatch.setenv("HG_PHASE18_USE_FAKE_ADAPTER", "true")
    monkeypatch.setenv("HG_PHASE18_PLATFORM", "moltbook")
    monkeypatch.setenv("HG_PHASE18_ACTION_TYPE", "publish_post")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    monkeypatch.setenv("HG_PHASE18_EXPECTED_CONTENT_SHA256", sha)
    live = _full_chain("fake-adapter", f, sha)
    result, deny = dispatch_live(live_permit_id=live.live_permit_id)
    assert result is not None
    assert result.verdict == "YELLOW_FAKE_ADAPTER_NOT_LIVE_GREEN"


def test_no_duplicate_live_dispatch(tmp_path, monkeypatch):
    reset_live_dispatch_count()
    monkeypatch.setenv("HG_PHASE18_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setenv("HG_PHASE18_OPERATOR_CONFIRMED", "true")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "true")
    monkeypatch.setenv("HG_PHASE18_USE_FAKE_ADAPTER", "true")
    monkeypatch.setenv("HG_PHASE18_PLATFORM", "moltbook")
    monkeypatch.setenv("HG_PHASE18_ACTION_TYPE", "publish_post")
    f = tmp_path / "p.md"
    f.write_text("hello", encoding="utf-8")
    sha = file_sha256(f)
    monkeypatch.setenv("HG_PHASE18_EXPECTED_CONTENT_SHA256", sha)
    live = _full_chain("dup-dispatch", f, sha)
    dispatch_live(live_permit_id=live.live_permit_id)
    result2, deny2 = dispatch_live(live_permit_id=live.live_permit_id)
    assert result2 is None
    assert "RED_MULTIPLE_LIVE_ACTIONS" in deny2
