"""Extended dry autonomy live read mode tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.extended_dry_autonomy.extended_runner import run_extended_dry_autonomy
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyConfig

VALID = json.dumps({
    "observation_summary": "Quiet.",
    "reasoning_summary": "Rest.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "live_read_provider_endurance")
    monkeypatch.setenv("HG_ANCHOR_ALLOW_PUSH", "false")
    monkeypatch.delenv("HG_ENABLE_LIVE_SOCIAL_READ", raising=False)
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_boot_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "boot"},
    )
    monkeypatch.setattr(
        "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_shutdown_anchor",
        lambda **kwargs: {"local_committed": True, "journal_receipt_id": "stop"},
    )
    monkeypatch.setattr(
        "hg_runtime.live_read_endurance.read_endurance_runner.probe_live_read_status",
        lambda **kwargs: {"status": "degraded", "verdict": "YELLOW_LIVE_READ_CREDENTIALS_MISSING", "receipt_ref": None},
    )


def test_allow_live_read_records_status(tmp_path, monkeypatch):
    ext_base = tmp_path / "ext"
    turn_base = tmp_path / "turns"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext_base))
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(turn_base))
    cfg = ExtendedDryAutonomyConfig(
        run_id="p16-ext",
        agent_id="zero",
        max_iterations=1,
        max_duration_seconds=60,
        turn_interval_seconds=0,
        checkpoint_every_iterations=1,
        allow_provider=True,
        allow_live_read=True,
    )

    def _invoke(_p, _r):
        return VALID

    monkeypatch.setattr(
        "hg_runtime.live_read_endurance.read_endurance_runner.read_once",
        lambda **kwargs: {"live_read_receipt_id": "lr-1", "freshness_status": "fresh", "verdict": "GREEN_LIVE_READ_ENDURANCE_COMPLETE", "success": True},
    )

    run = run_extended_dry_autonomy(cfg, extended_base=ext_base, turn_base=turn_base, provider_invoke=_invoke)
    hb_path = ext_base / "p16-ext" / "heartbeats.jsonl"
    assert hb_path.is_file()
    last = json.loads(hb_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "live_read_status" in last
    assert last["live_read_status"] in ("degraded", "unavailable", "available", "blocked")
    assert run.iteration_count >= 0
