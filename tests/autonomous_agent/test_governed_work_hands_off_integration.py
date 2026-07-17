"""Hands-off + governed work integration."""
from __future__ import annotations

import os

import pytest

from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config
from hg_runtime.hands_off_session.session_runner import run_hands_off_session


@pytest.fixture
def paths(tmp_path, monkeypatch):
    ho = tmp_path / "hands_off"
    ts = tmp_path / "task_selection"
    gw = tmp_path / "governed"
    turns = tmp_path / "turns"
    monkeypatch.setenv("HG_HANDS_OFF_FAST_TURNS", "1")
    monkeypatch.setenv("HG_GOVERNED_WORK_LOOP_ENABLED", "1")
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", ho)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_lock.STORE_ROOT", ho)
    monkeypatch.setattr("hg_runtime.task_selection.schema.STORE_ROOT", ts)
    monkeypatch.setattr("hg_runtime.task_selection.objective_universe.STORE_ROOT", ts)
    monkeypatch.setattr("hg_runtime.task_selection.objective_universe.UNIVERSE_DIR", ts / "universes")
    monkeypatch.setattr("hg_runtime.task_selection.task_candidate.STORE_ROOT", ts)
    monkeypatch.setattr("hg_runtime.task_selection.task_candidate.CANDIDATE_DIR", ts / "candidates")
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.STORE_ROOT", ts)
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.DECISION_DIR", ts / "decisions")
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.RECEIPT_DIR", ts / "receipts")
    monkeypatch.setattr("hg_runtime.governed_work_loop.schema.STORE_ROOT", gw)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.STORE_ROOT", gw)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_receipts.STORE_ROOT", gw)
    monkeypatch.setattr("hg_runtime.governed_work_loop.action_quota.QUOTA_DIR", gw / "quotas")
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.ENVELOPE_DIR", gw / "envelopes")
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.EXT_ENVELOPE_DIR", gw / "external_envelopes")
    return ho, turns, gw


def test_hands_off_records_governed_work_ref(paths):
    ho, turns, _ = paths
    from hg_runtime.governed_work_loop.work_envelope import create_demo_envelope

    env, _ = create_demo_envelope()
    config = validate_session_config(
        HandsOffSessionConfig(
            session_id="gov-int",
            agent_id="zero",
            objective_universe_ref="",
            governed_work_loop_enabled=True,
            work_envelope_ref=env.envelope_id,
            turn_interval_seconds=0.01,
            test_only_stop_after_observed_turns=1,
            created_at="2026-01-01T00:00:00+00:00",
        ),
        production_mode=False,
    )
    pf = run_hands_off_session(config, base=ho, turn_base=turns, production_mode=False)
    assert pf.turn_count >= 1
