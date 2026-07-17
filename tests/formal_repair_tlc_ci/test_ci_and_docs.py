"""CI honesty + docs consistency (mission cases 5-6, 14-18)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

WORKSPACE = Path(__file__).resolve().parents[2]


def _job():
    ci = yaml.safe_load((WORKSPACE / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    return ci.get("formal_tlc_required")


def test_required_ci_job_exists():
    # case 14
    job = _job()
    assert job is not None
    assert job["stage"] == "validate"


def test_required_ci_job_includes_require_tlc():
    # case 15
    blob = "\n".join(str(s) for s in _job()["script"])
    assert "--require-tlc" in blob


def test_required_ci_job_not_optional():
    # case 16
    job = _job()
    assert not job.get("allow_failure", False)
    assert job.get("when") not in ("manual",)


def test_docs_cannot_say_ci_enforced_without_job():
    # case 17: FORMAL_STATUS names the exact job it relies on, and that job exists
    fs = (WORKSPACE / "docs/FORMAL_STATUS.md").read_text(encoding="utf-8")
    assert "formal_tlc_required" in fs
    assert _job() is not None
    # the honest limit is stated: no pipeline execution yet
    assert "pending" in fs and "push window" in fs


def test_formal_status_rows_match_ci_scope():
    # case 18: the four enforced models are exactly the runner's models
    fs = (WORKSPACE / "docs/FORMAL_STATUS.md").read_text(encoding="utf-8")
    for model in ("SafetyGate", "Watchdog", "Halt", "Composition"):
        assert model in fs
    runner_src = (WORKSPACE / "scripts/run_formal_tlc.py").read_text(encoding="utf-8")
    for name in ("safety_gate", "watchdog", "halt", "composition"):
        assert f'("{name}"' in runner_src


def test_green_claims_backed_by_tlc_results():
    # cases 5-6: FORMAL_STATUS may only say GREEN for SG/WD if a recorded repair
    # bundle with GREEN verdicts exists on disk
    fs = (WORKSPACE / "docs/FORMAL_STATUS.md").read_text(encoding="utf-8")
    if "RUN RECORDED 2026-07-04" in fs:
        root = WORKSPACE / "docs/proofs/formal_repair_tlc_ci"
        bundles = sorted(d for d in root.iterdir() if d.is_dir()) if root.exists() else []
        assert bundles, "FORMAL_STATUS cites 2026-07-04 runs but no repair bundle exists"
        latest = bundles[-1]
        summary = json.loads((latest / "formal_tlc_result.json").read_text(encoding="utf-8"))
        by_model = {e["model"]: e["verdict"] for e in summary["results"]}
        assert by_model["safety_gate"] == "GREEN_INVARIANTS_HELD_BOUNDED"
        assert by_model["watchdog"] == "GREEN_INVARIANTS_HELD_BOUNDED"


def test_watchdog_stale_latch_fix():
    # FRC-011 runtime delta: a new disconnect invalidates a prior gate pass
    from hg_embodied.actuator.watchdog import Watchdog
    wd = Watchdog(robot_id="frc-test")
    wd.on_comms_lost()
    wd.state = "settled"
    assert wd.pass_resume_gate(fresh_env_model=True) is True
    assert wd.resume_gate_passed is True
    wd.on_comms_lost()  # second disconnect
    assert wd.resume_gate_passed is False
    result = wd.on_comms_restored()
    assert result["can_resume"] is False
