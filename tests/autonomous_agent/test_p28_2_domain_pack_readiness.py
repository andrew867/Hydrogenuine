"""P28-2 domain pack readiness tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_readiness_gate import evaluate_domain_readiness_gate
from hg_runtime.domain_pack_runtime.gate import validate_p28_2_gate
from hg_runtime.domain_pack_runtime.redaction import secret_scan
from hg_runtime.domain_pack_runtime.schemas import READINESS_STATES


def _repo():
    return Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P28_2_DOMAIN_PACK_READINESS",
        "p28_1_green": True,
        "readiness_records_written": True,
        "boundary_matrix_written": True,
        "readiness_states_valid": True,
        "readiness_not_deployment": True,
        "refusal_boundary_enforced": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p28_2_readiness_states():
    layer = evaluate_domain_readiness_gate(_repo())
    states = {row["readiness_state"] for row in layer["domain_pack_readiness_records"]}
    assert states <= READINESS_STATES


def test_p28_2_readiness_not_deployment():
    layer = evaluate_domain_readiness_gate(_repo())
    assert all(row["readiness_is_not_deployment_permission"] for row in layer["domain_pack_readiness_records"])


def test_p28_2_secret_scan():
    assert secret_scan(evaluate_domain_readiness_gate(_repo())) is True


def test_p28_2_gate_passes():
    assert validate_p28_2_gate(_summary())["ok"] is True
