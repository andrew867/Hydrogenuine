"""Supervised rehearsal postflight tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.supervised_rehearsal.errors import PostflightError
from hg_runtime.supervised_rehearsal.postflight import run_postflight
from hg_runtime.supervised_rehearsal.rehearsal_runner import run_supervised_rehearsal
from hg_runtime.supervised_rehearsal.schema import SupervisedRehearsalConfig, now_iso


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
    monkeypatch.setattr("hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir", lambda run_id, base=None: (tmp_path / "rehearsals" / run_id))
    return tmp_path


def test_postflight_after_successful_run(tmp_path):
    result = run_supervised_rehearsal(
        SupervisedRehearsalConfig(
            run_id="run-pf", agent_id="zero", max_turns=1, created_at=now_iso()
        ).with_hash(),
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert result.postflight_ref
    pf = run_postflight(
        run_id="run-pf",
        agent_id="zero",
        started_at=result.started_at,
        turn_count=result.turn_count,
        rehearsal_base=tmp_path / "rehearsals",
        turn_base=tmp_path / "turns",
    )
    assert pf.replay_verdict == "GREEN_REPLAY_OK"
    assert pf.turn_count == 1


def test_postflight_detects_missing_journal(tmp_path):
    with pytest.raises(PostflightError):
        run_postflight(
            run_id="missing",
            agent_id="zero",
            started_at=now_iso(),
            turn_count=1,
            rehearsal_base=tmp_path / "rehearsals",
            turn_base=tmp_path / "turns",
        )
