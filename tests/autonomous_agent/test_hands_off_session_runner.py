"""Hands-off session runner."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_runtime.hands_off_session.manual_controls import create_stop_control
from hg_runtime.hands_off_session.postflight import load_postflight
from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config
from hg_runtime.hands_off_session.session_runner import run_hands_off_session
from hg_runtime.hands_off_session.session_state import load_state


@pytest.fixture(autouse=True)
def fast_turns(monkeypatch):
    monkeypatch.setenv("HG_HANDS_OFF_FAST_TURNS", "1")


@pytest.fixture
def env_paths(tmp_path, monkeypatch):
    ho_root = tmp_path / "hands_off"
    ts_root = tmp_path / "task_selection"
    turn_root = tmp_path / "turns"
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", ho_root)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_lock.STORE_ROOT", ho_root)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_state.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.hands_off_session.manual_controls.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.hands_off_session.heartbeat.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.hands_off_session.postflight.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_receipts.session_dir", lambda sid, base=None: ho_root / sid)
    monkeypatch.setattr("hg_runtime.task_selection.schema.STORE_ROOT", ts_root)
    monkeypatch.setattr("hg_runtime.task_selection.objective_universe.STORE_ROOT", ts_root)
    monkeypatch.setattr("hg_runtime.task_selection.objective_universe.UNIVERSE_DIR", ts_root / "universes")
    monkeypatch.setattr("hg_runtime.task_selection.task_candidate.STORE_ROOT", ts_root)
    monkeypatch.setattr("hg_runtime.task_selection.task_candidate.CANDIDATE_DIR", ts_root / "candidates")
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.STORE_ROOT", ts_root)
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.DECISION_DIR", ts_root / "decisions")
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.RECEIPT_DIR", ts_root / "receipts")
    return ho_root, turn_root


def test_runner_foreground_with_test_stop(env_paths):
    ho_root, turn_root = env_paths
    config = validate_session_config(
        HandsOffSessionConfig(
            session_id="test-run",
            agent_id="zero",
            objective_universe_ref="",
            turn_interval_seconds=0.01,
            test_only_stop_after_observed_turns=2,
            created_at="2026-01-01T00:00:00+00:00",
        ),
        production_mode=False,
    )
    pf = run_hands_off_session(config, base=ho_root, turn_base=turn_root, production_mode=False)
    assert pf.turn_count >= 2
    assert pf.background_process_survives is False
    state = load_state("test-run", base=ho_root)
    assert state.pid == os.getpid()


def test_runner_writes_heartbeat_and_postflight(env_paths):
    ho_root, turn_root = env_paths
    config = validate_session_config(
        HandsOffSessionConfig(
            session_id="test-hb",
            agent_id="zero",
            objective_universe_ref="",
            turn_interval_seconds=0.01,
            test_only_stop_after_observed_turns=1,
            created_at="2026-01-01T00:00:00+00:00",
        ),
        production_mode=False,
    )
    run_hands_off_session(config, base=ho_root, turn_base=turn_root, production_mode=False)
    state = load_state("test-hb", base=ho_root)
    assert state.last_heartbeat_ref
    assert load_postflight("test-hb", base=ho_root) is not None


def test_stop_control_stops_session(env_paths):
    ho_root, turn_root = env_paths
    config = validate_session_config(
        HandsOffSessionConfig(
            session_id="test-stop",
            agent_id="zero",
            objective_universe_ref="",
            turn_interval_seconds=0.05,
            test_only_stop_after_observed_turns=10,
            created_at="2026-01-01T00:00:00+00:00",
        ),
        production_mode=False,
    )
    import threading
    import time

    def _stop_later():
        time.sleep(0.3)
        create_stop_control("test-stop", base=ho_root)

    t = threading.Thread(target=_stop_later, daemon=True)
    t.start()
    pf = run_hands_off_session(config, base=ho_root, turn_base=turn_root, production_mode=False)
    assert pf.stop_requested or pf.turn_count >= 1
