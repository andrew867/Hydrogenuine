"""P28-0 domain pack schema tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.fixtures import build_p28_0_layer
from hg_runtime.domain_pack_runtime.gate import validate_p28_0_gate
from hg_runtime.domain_pack_runtime.redaction import secret_scan
from hg_runtime.domain_pack_runtime.schemas import P28_INVARIANTS, PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES


def _layer():
    return build_p28_0_layer(Path(__file__).resolve().parents[2])


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P28_0_DOMAIN_PACK_SCHEMAS",
        "schemas_declared": True,
        "policy_written": True,
        "pack_written": True,
        "link_written": True,
        "boundary_written": True,
        "readiness_written": True,
        "domain_pack_not_permission": True,
        "domain_label_not_expertise": True,
        "readiness_not_deployment": True,
        "skill_link_not_authority": True,
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


def test_p28_0_record_types():
    assert len(RECORD_TYPES) == 6


def test_p28_0_invariants():
    assert len(P28_INVARIANTS) == 10


def test_p28_0_domain_pack_not_permission():
    assert _layer()["policy"]["domain_pack_is_not_permission"] is True
    assert _layer()["domain_packs"][0]["domain_pack_is_not_permission"] is True


def test_p28_0_phase19_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_p28_0_secret_scan():
    assert secret_scan(_layer()) is True


def test_p28_0_gate_passes():
    assert validate_p28_0_gate(_summary())["ok"] is True
