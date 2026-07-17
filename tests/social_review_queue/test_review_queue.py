"""Social review queue tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.bounded_soak.schema import BoundedSoakProfile
from hg_runtime.bounded_soak.supervisor import _run_task
from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.schema import SoakBudget
from hg_runtime.exciton.control_boundary import ExcitonControlBoundary, FORBIDDEN_CONTROLS
from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton.schema import ExcitonControlKind, ExcitonControlRequest, new_id
from hg_runtime.social_capability.review_queue import (
    LEGACY_INCIDENT,
    approve_item,
    deny_item,
    enqueue_curated_post,
    import_from_soak_run,
    is_publish_paused,
    load_queue,
    pause_live_publish,
    pick_approved_for_publish,
    queue_path,
    resume_approved_only,
)
from hg_runtime.social_capability.review_schema import SocialReviewStatus
from datetime import datetime, timezone


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "soak_run"
    d.mkdir()
    (d / "operator_publish_confirmation.json").write_text(
        json.dumps({"confirmed": True, "max_posts": 3}),
        encoding="utf-8",
    )
    return d


def test_queued_draft_appears_in_review_queue(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "hello world"}
    item = enqueue_curated_post(run_dir, post)
    queue = load_queue(run_dir)
    assert len(queue.items) == 1
    assert queue.items[0].status == SocialReviewStatus.QUEUED
    assert item.queue_item_id


def test_unreviewed_cannot_publish(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "hello world"}
    enqueue_curated_post(run_dir, post)
    (run_dir / "run_control.json").write_text(
        json.dumps({"approved_only_mode": True, "allow_live_social_publish": True}),
        encoding="utf-8",
    )
    assert pick_approved_for_publish(run_dir) is None


def test_approved_can_publish_once(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "hello world"}
    item = enqueue_curated_post(run_dir, post)
    (run_dir / "run_control.json").write_text(
        json.dumps({"approved_only_mode": True, "allow_live_social_publish": True}),
        encoding="utf-8",
    )
    result = approve_item(run_dir, item.queue_item_id, operator_ref="test-op")
    assert result["ok"]
    picked = pick_approved_for_publish(run_dir)
    assert picked is not None
    assert picked.queue_item_id == item.queue_item_id


def test_denied_cannot_publish(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "hello world"}
    item = enqueue_curated_post(run_dir, post)
    deny_item(run_dir, item.queue_item_id, operator_ref="test-op", reason="not tonight")
    assert pick_approved_for_publish(run_dir) is None


def test_approve_all_unavailable():
    assert ExcitonControlKind.APPROVE_ALL in FORBIDDEN_CONTROLS


def test_direct_publish_denied():
    boundary = ExcitonControlBoundary()
    req = ExcitonControlRequest(new_id("req"), ExcitonControlKind.DIRECT_PUBLISH)
    decision = boundary.decide(req)
    assert decision.decision.value == "DENY"


def test_operator_confirmation_does_not_approve_items(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "hello world"}
    enqueue_curated_post(run_dir, post)
    assert (run_dir / "operator_publish_confirmation.json").is_file()
    assert pick_approved_for_publish(run_dir) is None


def test_no_credentials_in_queue(run_dir: Path):
    post = {"post_id": "overnight-calm-2", "surface": "moltbook", "topic": "craft", "body": "safe text"}
    enqueue_curated_post(run_dir, post)
    payload = json.loads(queue_path(run_dir).read_text(encoding="utf-8"))
    assert not scan_forbidden(payload)


def test_hidden_cot_not_in_preview(run_dir: Path):
    post = {
        "post_id": "overnight-calm-2",
        "surface": "moltbook",
        "topic": "craft",
        "body": "public text chain_of_thought secret reasoning",
    }
    item = enqueue_curated_post(run_dir, post)
    assert "chain_of_thought" not in item.sanitized_preview.lower() or "[redacted]" in item.sanitized_preview


def test_pause_blocks_publish(run_dir: Path):
    pause_live_publish(run_dir)
    assert is_publish_paused(run_dir)
    profile = BoundedSoakProfile(
        profile_id="test",
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
    assert "paused" in res.detail.lower() or "NO_APPROVED" in res.detail


def test_legacy_incident_import(run_dir: Path):
    (run_dir / "curated_post_index.json").write_text(
        json.dumps({"used_post_ids": ["overnight-calm-1"]}),
        encoding="utf-8",
    )
    result = import_from_soak_run(run_dir)
    assert result["legacy_incident_recorded"]
    queue = load_queue(run_dir)
    legacy = [i for i in queue.items if i.incident_class == LEGACY_INCIDENT]
    assert len(legacy) == 1
    assert legacy[0].status == SocialReviewStatus.PUBLISHED_LEGACY_UNCONFIRMED
