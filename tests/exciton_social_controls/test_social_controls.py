"""EXCITON social operator controls — wired, per-item approval, no approve-all, no direct publish."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.exciton.action_handlers import handle_control
from hg_runtime.exciton.control_matrix import get_entry
from hg_runtime.social_capability.draft import load_curated_posts
from hg_runtime.social_capability.review_queue import enqueue_curated_post, load_queue
from hg_runtime.social_capability.review_schema import SocialReviewStatus

CONTROLS = ("REFRESH_SOCIAL_STATUS", "GENERATE_SOCIAL_DRAFT", "QUEUE_SOCIAL_DRAFT", "APPROVE_SOCIAL_PUBLISH")


def _run_dir(tmp_path: Path) -> Path:
    rd = tmp_path / ".hg-local" / "soak" / "runs" / "FIXTURE"
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "run_control.json").write_text(json.dumps({"allow_live_social_publish": False, "max_posts_total": 0}) + "\n", encoding="utf-8")
    return rd


def _base(tmp_path: Path, rd: Path) -> dict:
    return {"workspace": str(tmp_path), "run_dir": str(rd)}


def test_all_controls_registered_and_not_forbidden():
    for cid in CONTROLS:
        e = get_entry(cid)
        assert e is not None
        assert not e.forbidden


def test_generate_draft_does_not_publish(tmp_path):
    rd = _run_dir(tmp_path)
    r = handle_control("GENERATE_SOCIAL_DRAFT", _base(tmp_path, rd))
    assert r["ok"] is True
    assert r["draft_id"]
    assert r["published"] is False
    assert r["receipt_ref"]


def test_queue_draft_creates_item(tmp_path):
    rd = _run_dir(tmp_path)
    r = handle_control("QUEUE_SOCIAL_DRAFT", _base(tmp_path, rd))
    assert r["ok"] is True
    assert r["queue_item_id"]
    queued = [i for i in load_queue(rd).items if i.status == SocialReviewStatus.QUEUED]
    assert len(queued) >= 1


def test_approve_publish_approves_exactly_one(tmp_path):
    rd = _run_dir(tmp_path)
    posts = load_curated_posts()
    assert len(posts) >= 2
    enqueue_curated_post(rd, posts[0])
    enqueue_curated_post(rd, posts[1])
    r = handle_control("APPROVE_SOCIAL_PUBLISH", _base(tmp_path, rd))
    assert r["ok"] is True
    assert r["published"] is False
    q = load_queue(rd)
    approved = [i for i in q.items if i.status == SocialReviewStatus.APPROVED]
    still_queued = [i for i in q.items if i.status == SocialReviewStatus.QUEUED]
    published = [i for i in q.items if i.status == SocialReviewStatus.PUBLISHED]
    assert len(approved) == 1  # exactly one — no approve-all
    assert len(still_queued) == 1  # the other remains for separate review
    assert len(published) == 0  # never publishes


def test_controls_show_disabled_reason_without_run(tmp_path):
    for cid in ("QUEUE_SOCIAL_DRAFT", "APPROVE_SOCIAL_PUBLISH"):
        r = handle_control(cid, {"workspace": str(tmp_path)})
        assert r["ok"] is False
        assert r["disabled_reason"]


def test_no_authority_conversion(tmp_path):
    rd = _run_dir(tmp_path)
    for cid in CONTROLS:
        r = handle_control(cid, _base(tmp_path, rd))
        assert r["permission_granted"] is False
        assert r["authority_created"] is False
