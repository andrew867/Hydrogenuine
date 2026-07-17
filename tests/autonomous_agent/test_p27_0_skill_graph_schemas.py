"""P27-0 skill graph schema tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.batch_gate import validate_p27_0_gate
from hg_runtime.skill_graph.fixtures import build_p27_0_layer
from hg_runtime.skill_graph.p27_schemas import P27_INVARIANTS, PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES
from hg_runtime.skill_graph.redaction import secret_scan


def _layer():
    return build_p27_0_layer(Path(__file__).resolve().parents[2])


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P27_0_SKILL_GRAPH_SCHEMAS",
        "schemas_declared": True,
        "policy_written": True,
        "skill_written": True,
        "edge_written": True,
        "link_written": True,
        "candidate_written": True,
        "result_written": True,
        "skill_not_authority": True,
        "reuse_not_proof": True,
        "transfer_not_competence": True,
        "memory_source_required": True,
        "provenance_required": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p27_0_record_types():
    assert len(RECORD_TYPES) == 7


def test_p27_0_invariants():
    assert len(P27_INVARIANTS) == 10


def test_p27_0_skill_not_authority():
    assert _layer()["policy"]["skill_is_not_authority"] is True
    assert _layer()["skill_records"][0]["skill_treated_as_authority"] is False


def test_p27_0_phase19_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_p27_0_secret_scan():
    assert secret_scan(_layer()) is True


def test_p27_0_gate_passes():
    assert validate_p27_0_gate(_summary())["ok"] is True
