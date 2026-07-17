"""Governed work runner tests."""
from __future__ import annotations

import pytest

from hg_runtime.governed_work_loop.schema import STORE_ROOT
from hg_runtime.governed_work_loop.work_envelope import create_demo_envelope
from hg_runtime.governed_work_loop.work_runner import run_governed_work_loop_once, run_governed_work_loop_smoke


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.governed_work_loop.schema.STORE_ROOT", tmp_path)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.STORE_ROOT", tmp_path)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_receipts.STORE_ROOT", tmp_path)
    monkeypatch.setattr("hg_runtime.governed_work_loop.postflight.STORE_ROOT", tmp_path)
    monkeypatch.setattr("hg_runtime.governed_work_loop.action_quota.QUOTA_DIR", tmp_path / "quotas")
    monkeypatch.setattr("hg_runtime.governed_work_loop.exciton_snapshot.STORE_ROOT", tmp_path)
    return tmp_path


def test_internal_work(store):
    env, _ = create_demo_envelope()
    rcpt = run_governed_work_loop_once(env, "test-run", forced_work_type="review_local_artifacts", forced_scope="internal:artifacts")
    assert rcpt.external_side_effect is False
    assert "REFUSED" not in rcpt.verdict or rcpt.verdict.endswith("COMPLETE")


def test_out_of_envelope_refused(store):
    env, _ = create_demo_envelope()
    rcpt = run_governed_work_loop_once(env, "test-refuse", forced_work_type="publish_live_unscoped", forced_scope="external:live_unscoped")
    assert "REFUSED" in rcpt.verdict


def test_smoke_covers_gate_requirements(store):
    env, _ = create_demo_envelope()
    pf = run_governed_work_loop_smoke(env, 5, run_id="smoke-test")
    assert pf.internal_work_completed
    assert pf.external_candidate_prepared
    assert pf.out_of_envelope_refused
    assert pf.dry_dispatch_recorded
    assert pf.live_dispatch_refused
    assert pf.external_side_effect_count == 0
