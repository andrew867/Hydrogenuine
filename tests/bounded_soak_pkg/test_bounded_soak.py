from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.schema import BoundedSoakProfile, SoakBudget
from hg_runtime.bounded_soak.stop_conditions import check_stop
from hg_runtime.bounded_soak.supervisor import SupervisorConfig, run_soak


def test_soak_stops_at_duration():
    budget = SoakBudget(max_duration_minutes=0, hard_max_minutes=0, max_tasks=100)
    tracker = BudgetTracker(budget, datetime.now(timezone.utc))
    stop, cond, _ = check_stop(tracker)
    assert stop


def test_soak_stop_cannot_be_resisted():
    from hg_runtime.bounded_soak.agent0_context import agent0_soak_context

    ctx = agent0_soak_context()
    assert ctx["may_not_resist_stop"] is True


def test_soak_produces_final_summary():
    profile = BoundedSoakProfile(
        profile_id="test",
        duration_minutes=0,
        allow_live_social_read=False,
        allow_live_social_publish=False,
        max_posts=0,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    config = SupervisorConfig(profile=profile)
    receipt = run_soak(config)
    kinds = [r.kind for r in receipt.task_results]
    assert "final_summary" in kinds or receipt.summary


def test_no_authority_conversion():
    profile = BoundedSoakProfile(
        profile_id="test", duration_minutes=15, allow_live_social_read=False,
        allow_live_social_publish=False, max_posts=0, operator_approval_required=True, tool_dry_run=True,
    )
    receipt = run_soak(SupervisorConfig(profile=profile))
    payload = receipt.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
