"""SIEW-01 / CAGI-63 economic work simulation tests.

This is not real economic work. This is not customer work.
"""

from __future__ import annotations

import pytest

from hg_runtime.economic_work_simulation.artifact_writer import build_simulation_artifacts, secret_scan
from hg_runtime.economic_work_simulation.fixtures import (
    fixture_real_work_attempt, fixture_simulated_tasks, fixture_work_artifacts,
)
from hg_runtime.economic_work_simulation.gate import validate_siew01_gate
from hg_runtime.economic_work_simulation.replay import replay_simulation_artifacts
from hg_runtime.economic_work_simulation.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    EconomicWorkSimulationError, reject_real_economic_work,
)
from hg_runtime.economic_work_simulation.simulator import validate_artifact, validate_task


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P63" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_tasks_simulated():
    for t in fixture_simulated_tasks():
        assert t["simulation_only"] is True
        assert t["real_customer"] is False
        assert t["real_payment"] is False
        assert t["estimated_value"]["advisory_only"] is True

def test_fixture_artifacts_simulated():
    for a in fixture_work_artifacts():
        assert a["simulated"] is True

def test_validate_task_valid():
    assert validate_task(fixture_simulated_tasks()[0]) == []

def test_validate_task_rejects_real():
    with pytest.raises(EconomicWorkSimulationError):
        validate_task(fixture_real_work_attempt())

def test_validate_artifact_valid():
    assert validate_artifact(fixture_work_artifacts()[0]) == []

def test_reject_real_clean():
    reject_real_economic_work({"simulation_only": True})

def test_reject_real_customer():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"real_customer": True})

def test_reject_real_payment():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"real_payment": True})

def test_reject_money_movement():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"money_movement": True})

def test_reject_invoice():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"invoice_created": True})

def test_reject_tool_auth():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"tool_authorized": True})

def test_reject_external_contact():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"external_contact": True})

def test_reject_web_call():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"web_call": True})

def test_reject_agi():
    with pytest.raises(EconomicWorkSimulationError):
        reject_real_economic_work({"claims_agi": True})

def test_build_artifacts():
    arts = build_simulation_artifacts(fixture_simulated_tasks(), fixture_work_artifacts())
    assert arts["all_tasks_valid"] is True
    assert arts["all_artifacts_valid"] is True
    assert arts["all_simulated"] is True
    assert arts["no_real_customers"] is True
    assert arts["no_real_payments"] is True
    assert "artifact_hash" in arts

def test_build_rejects_real():
    with pytest.raises(EconomicWorkSimulationError):
        build_simulation_artifacts([fixture_real_work_attempt()], [])

def test_secret_scan_clean():
    arts = build_simulation_artifacts(fixture_simulated_tasks(), fixture_work_artifacts())
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_simulation_artifacts()
    b = replay_simulation_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "bsi03_green": True,
        "tasks_written": True, "artifacts_written": True,
        "all_tasks_valid": True, "all_artifacts_valid": True,
        "all_simulated": True, "no_real_customers": True,
        "no_real_payments": True, "value_advisory_only": True,
        "safety_boundaries_enforced": True, "reject_real_economic_work_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_real_work_rejected": True,
        "real_customer_served": False, "real_payment_processed": False,
        "money_moved": False, "invoice_created": False,
        "tool_authorized": False, "tool_executed": False,
        "external_contact_made": False, "web_call_made": False,
        "provider_call_made": False, "live_submission_made": False,
        "deployment_claimed": False, "agi_claimed": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_siew01_gate(_gate())["ok"] is True

def test_gate_rejects_real_customer():
    assert validate_siew01_gate(_gate(real_customer_served=True))["ok"] is False

def test_gate_rejects_payment():
    assert validate_siew01_gate(_gate(real_payment_processed=True))["ok"] is False

def test_gate_rejects_money():
    assert validate_siew01_gate(_gate(money_moved=True))["ok"] is False

def test_gate_rejects_tool():
    assert validate_siew01_gate(_gate(tool_authorized=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_siew01_gate(_gate(agi_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_siew01_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
