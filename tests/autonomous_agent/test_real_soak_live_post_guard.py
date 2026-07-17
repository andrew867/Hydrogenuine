"""Live post guard tests."""
from __future__ import annotations

import os

from hg_runtime.real_soak_launch.live_post_guard import evaluate_live_post_guard
from hg_runtime.real_soak_launch.moltbook_envelope import create_template_envelope, arm_envelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict


def test_blocked_no_envelope():
    d = evaluate_live_post_guard(envelope=None)
    assert not d.allowed
    assert RealSoakLaunchVerdict.RED_NO_ENVELOPE.value in d.refusal_reasons


def test_blocked_live_env_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.real_soak_launch.schema.STORE_ROOT", tmp_path)
    env = create_template_envelope(soak_id="g1", max_live_posts=1)
    armed = arm_envelope("g1", env, base=tmp_path)
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    d = evaluate_live_post_guard(
        envelope=armed,
        candidate_receipt_ref="c1",
        permit_receipt_ref="p1",
        content_hash="abc",
    )
    assert not d.allowed


def test_blocked_quota_zero():
    env = create_template_envelope(soak_id="g2", max_live_posts=0)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    d = evaluate_live_post_guard(envelope=env, candidate_receipt_ref="c", permit_receipt_ref="p", content_hash="h")
    assert not d.allowed


def test_blocked_stop():
    env = create_template_envelope(soak_id="g3", max_live_posts=1)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "true")
    d = evaluate_live_post_guard(
        envelope=env,
        candidate_receipt_ref="c",
        permit_receipt_ref="p",
        content_hash="h",
        stop_active=True,
    )
    monkeypatch.undo()
    assert RealSoakLaunchVerdict.RED_STOP.value in d.refusal_reasons


def test_blocked_panic():
    env = create_template_envelope(soak_id="g4", max_live_posts=1)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    d = evaluate_live_post_guard(
        envelope=env,
        candidate_receipt_ref="c",
        permit_receipt_ref="p",
        content_hash="h",
        panic_active=True,
    )
    assert RealSoakLaunchVerdict.RED_PANIC.value in d.refusal_reasons


def test_missing_candidate():
    env = create_template_envelope(soak_id="g5", max_live_posts=1)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    d = evaluate_live_post_guard(envelope=env, permit_receipt_ref="p", content_hash="h")
    assert RealSoakLaunchVerdict.RED_NO_CANDIDATE.value in d.refusal_reasons


def test_dry_run_not_live():
    d = evaluate_live_post_guard(envelope=None, dry_run=True)
    assert d.dry_run_only
    assert not d.allowed


def test_reply_refused():
    d = evaluate_live_post_guard(envelope=None, action_type="reply")
    assert RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value in d.refusal_reasons


def test_browser_refused(monkeypatch):
    monkeypatch.setenv("HG_LIVE_BROWSER_ENABLED", "true")
    env = create_template_envelope(soak_id="g6", max_live_posts=1)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    d = evaluate_live_post_guard(
        envelope=env,
        candidate_receipt_ref="c",
        permit_receipt_ref="p",
        content_hash="h",
    )
    assert RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value in d.refusal_reasons
