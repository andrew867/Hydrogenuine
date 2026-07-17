"""Bounded soak review queue integration tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.schema import BoundedSoakProfile, SoakBudget
from hg_runtime.bounded_soak.supervisor import _run_task
from hg_runtime.social_capability.review_queue import enqueue_curated_post, pause_live_publish


def test_curated_queue_task(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    profile = BoundedSoakProfile(
        profile_id="t",
        duration_minutes=60,
        allow_live_social_read=True,
        allow_live_social_publish=False,
        max_posts=0,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    budget = SoakBudget(max_duration_minutes=60, hard_max_minutes=60, max_posts=3)
    tracker = BudgetTracker(budget, datetime.now(timezone.utc))
    res = _run_task("curated_queue", profile, tracker, run_dir=run_dir)
    assert "curated_queued" in res.detail or "curated_queue" in res.detail


def test_publish_with_no_approved_items(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_control.json").write_text(
        json.dumps({"approved_only_mode": True, "allow_live_social_publish": True}),
        encoding="utf-8",
    )
    post = {"post_id": "overnight-calm-3", "surface": "moltbook", "topic": "craft", "body": "text"}
    enqueue_curated_post(run_dir, post)
    profile = BoundedSoakProfile(
        profile_id="t",
        duration_minutes=60,
        allow_live_social_read=True,
        allow_live_social_publish=True,
        max_posts=3,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    budget = SoakBudget(max_duration_minutes=60, hard_max_minutes=60, max_posts=3)
    tracker = BudgetTracker(budget, datetime.now(timezone.utc))
    res = _run_task("curated_publish", profile, tracker, run_dir=run_dir)
    assert res.detail == "NO_APPROVED_ITEMS"


def test_paused_skips_publish(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    pause_live_publish(run_dir)
    profile = BoundedSoakProfile(
        profile_id="t",
        duration_minutes=60,
        allow_live_social_read=True,
        allow_live_social_publish=True,
        max_posts=3,
        operator_approval_required=True,
        tool_dry_run=True,
    )
    budget = SoakBudget(max_duration_minutes=60, hard_max_minutes=60, max_posts=3)
    tracker = BudgetTracker(budget, datetime.now(timezone.utc))
    res = _run_task("curated_publish", profile, tracker, run_dir=run_dir)
    assert "paused" in res.detail.lower()
