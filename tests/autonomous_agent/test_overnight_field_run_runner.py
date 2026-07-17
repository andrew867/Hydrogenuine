"""Overnight field run runner tests."""
from __future__ import annotations

import os

import pytest

from hg_runtime.overnight_field_run.field_run_config import build_smoke_config
from hg_runtime.overnight_field_run.field_run_postflight import load_postflight
from hg_runtime.overnight_field_run.field_run_runner import run_overnight_field_session
from hg_runtime.overnight_field_run.schema import OvernightFieldRunVerdict
from hg_runtime.overnight_field_run.wake_report import load_wake_report


@pytest.fixture(autouse=True)
def fast_turns(monkeypatch):
    monkeypatch.setenv("HG_HANDS_OFF_FAST_TURNS", "1")


@pytest.fixture
def env_paths(tmp_path, monkeypatch):
    field_root = tmp_path / "overnight"
    ho_root = tmp_path / "hands_off"
    ts_root = tmp_path / "task_selection"
    gw_root = tmp_path / "governed_work"
    turn_root = tmp_path / "turns"
    monkeypatch.setattr("hg_runtime.overnight_field_run.schema.STORE_ROOT", field_root)
    monkeypatch.setattr("hg_runtime.overnight_field_run.field_run_lock.STORE_ROOT", field_root)
    monkeypatch.setattr("hg_runtime.overnight_field_run.field_run_state.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
    monkeypatch.setattr("hg_runtime.overnight_field_run.field_run_receipts.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
    monkeypatch.setattr("hg_runtime.overnight_field_run.wake_report.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
    monkeypatch.setattr("hg_runtime.overnight_field_run.continuity_audit.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
    monkeypatch.setattr("hg_runtime.overnight_field_run.field_run_postflight.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
    monkeypatch.setattr("hg_runtime.overnight_field_run.incident_summary.field_run_dir", lambda fid, base=None: (base or field_root) / fid)
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
    monkeypatch.setattr("hg_runtime.governed_work_loop.schema.STORE_ROOT", gw_root)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.STORE_ROOT", gw_root)
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.ENVELOPE_DIR", gw_root / "envelopes")
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.EXT_ENVELOPE_DIR", gw_root / "external_envelopes")
    monkeypatch.setattr("hg_runtime.governed_work_loop.action_quota.STORE_ROOT", gw_root)
    monkeypatch.setattr("hg_runtime.governed_work_loop.action_quota.QUOTA_DIR", gw_root / "quotas")
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_receipts.STORE_ROOT", gw_root)
    return field_root, ho_root, turn_root


def test_infrastructure_smoke_runs(env_paths):
    field_root, ho_root, turn_root = env_paths
    config = build_smoke_config(field_run_id="runner-smoke", observed_turns=2)
    pf = run_overnight_field_session(config, base=field_root, ho_base=ho_root, turn_base=turn_root)
    assert pf.turn_count >= 2
    assert pf.infrastructure_only is True
    assert pf.verdict == OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value
    assert pf.background_process_survives is False
    assert load_wake_report("runner-smoke", base=field_root) is not None
    assert load_postflight("runner-smoke", base=field_root) is not None


def test_no_background_after_stop(env_paths):
    field_root, ho_root, turn_root = env_paths
    config = build_smoke_config(field_run_id="runner-bg", observed_turns=1)
    pf = run_overnight_field_session(config, base=field_root, ho_base=ho_root, turn_base=turn_root)
    assert pf.background_process_survives is False
    assert os.getpid() > 0
