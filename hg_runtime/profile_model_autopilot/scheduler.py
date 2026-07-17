"""Autopilot scheduler — orchestrates propose -> dispose -> receipts (fixture)."""

from __future__ import annotations

from .proposal import propose, dispose
from .task_selector import build_curiosity_queue
from .resource_budget import default_budget
from .model_slots import default_policy


def autopilot_policy_snapshot() -> dict:
    from .model_slots import policy_snapshot
    from .resource_budget import budget_snapshot
    return {
        "model_slot_policy": policy_snapshot(),
        "resource_budget": budget_snapshot(),
        "zero_may_propose": True,
        "runtime_disposes": True,
        "operator_is_final_reviewer": True,
        "zero_self_authorizes": False,
        "permanent_main_brain_switch_by_zero": False,
    }


def run_fixture_cycle(applied_at: str, max_tasks: int = 6) -> dict:
    """Build a bounded fixture cycle: propose tasks, dispose, collect receipts."""
    tasks = build_curiosity_queue(max_tasks=max_tasks)
    proposals = []
    decisions = []
    for t in tasks:
        p = propose(
            proposal_kind="task_selection", proposed_at=applied_at,
            task_id=t.task_id, research_seed_id=t.research_seed_id,
            task_scope=t.task_kind, reason=t.reason,
            requested_token_budget=t.token_budget,
            requested_wallclock_budget_seconds=t.wallclock_budget_seconds,
            browsing_requested=t.requires_browsing,
        )
        proposals.append(p)
        decisions.append(dispose(p, decided_at=applied_at))
    return {
        "tasks": tasks,
        "proposals": proposals,
        "decisions": decisions,
        "policy": autopilot_policy_snapshot(),
    }
