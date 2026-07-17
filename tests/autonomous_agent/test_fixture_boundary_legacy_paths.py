"""Legacy fixture path boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.overnight_draft import (  # noqa: E402
    OvernightDraftPolicy,
    OvernightDraftSoakConfig,
    run_overnight_draft_soak,
)
from hg_runtime.bounded_soak.supervisor import SupervisorConfig, _run_task  # noqa: E402
from hg_runtime.bounded_soak.schema import BoundedSoakProfile  # noqa: E402
from hg_runtime.bounded_soak.budget import BudgetTracker, SoakBudget  # noqa: E402
from hg_runtime.exciton.agent0_context import build_exciton_agent0_context  # noqa: E402
from hg_runtime.fixture_policy import FixtureUseDenied  # noqa: E402
from hg_runtime.social_capability.read import read_social  # noqa: E402
from hg_runtime.social_capability.schema import SocialReadRequest, SocialSurface, new_id  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch):
    for key in (
        "HG_RUNTIME_MODE",
        "HG_ALLOW_FIXTURE_MODE",
        "HG_COGNITIVE_SOAK_ACTIVE",
        "HG_INFER_DRY_RUN",
        "HG_PROOF_REPLAY",
        "HG_SOCIAL_LIVE_READ",
        "HG_ENABLE_LIVE_SOCIAL_READ",
        "HG_MOLTBOOK_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        "hg_runtime.social_capability.credentials.load_operator_social_env",
        lambda **kw: [],
    )


def test_agent0_context_offline_fixture_false_by_default():
    ctx = build_exciton_agent0_context()
    assert ctx.temporal.get("offline_fixture") is False
    assert ctx.temporal.get("context_status") != "RED_FIXTURE_CONTEXT_USED_IN_RUNTIME"


def test_agent0_context_offline_fixture_requires_explicit_mode():
    ctx = build_exciton_agent0_context(offline_fixture=True)
    assert ctx.temporal.get("context_status") == "RED_FIXTURE_CONTEXT_USED_IN_RUNTIME"


def test_social_fixture_items_denied_without_fixture_mode():
    req = SocialReadRequest(new_id("read"), SocialSurface.FIXTURE, live=False)
    result = read_social(req)
    assert result.trust_disposition == "RED_FIXTURE_USED_IN_RUNTIME"
    assert len(result.items) == 0


def test_social_fixture_items_allowed_in_explicit_fixture_mode(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    req = SocialReadRequest(new_id("read"), SocialSurface.FIXTURE, live=False)
    result = read_social(req)
    assert result.trust_disposition == "YELLOW_FIXTURE_REHEARSAL"
    assert len(result.items) > 0


def test_legacy_overnight_draft_requires_fixture_rehearsal(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = OvernightDraftSoakConfig(
        run_dir=run_dir,
        policy=OvernightDraftPolicy(max_cycles=1, cycle_seconds=0),
    )
    with pytest.raises(FixtureUseDenied):
        run_overnight_draft_soak(config)


def test_legacy_rehearsal_allowed_when_explicit_fixture(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = OvernightDraftSoakConfig(
        run_dir=run_dir,
        policy=OvernightDraftPolicy(max_cycles=1, cycle_seconds=0),
    )
    with patch("hg_runtime.bounded_soak.overnight_draft.time.sleep"):
        summary = run_overnight_draft_soak(config)
    assert summary["not_autonomous_cognition"] is True
    assert summary["data_tier"] == "FIXTURE"
    assert summary["fixture_verdict"] == "YELLOW_FIXTURE_REHEARSAL"


def test_supervisor_does_not_force_fixture_surface_in_cognitive_mode(monkeypatch):
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    profile = BoundedSoakProfile(
        profile_id="test",
        duration_minutes=1,
        max_posts=0,
        allow_live_social_read=False,
        allow_live_social_publish=False,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    budget = SoakBudget(max_duration_minutes=1, hard_max_minutes=1, max_posts=0)
    tracker = BudgetTracker(budget, datetime.now(timezone.utc))
    result = _run_task("social_read_check", profile, tracker)
    assert "surface=local_text" in result.detail
    assert "FIXTURE" not in result.detail.upper() or "RED" in result.detail.upper()
