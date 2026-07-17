"""P27-2 skill graph transfer candidate tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.batch_gate import validate_p27_2_gate
from hg_runtime.skill_graph.redaction import secret_scan
from hg_runtime.skill_graph.transfer_candidate_builder import build_transfer_candidates


def _repo():
    return Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P27_2_SKILL_GRAPH_TRANSFER_CANDIDATES",
        "p27_1_green": True,
        "graph_index_written": True,
        "edges_written": True,
        "transfer_candidates_written": True,
        "negative_transfer_risk_recorded": True,
        "transfer_not_proof": True,
        "competence_not_claimed": True,
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


def test_p27_2_transfer_candidates():
    layer = build_transfer_candidates(_repo())
    assert len(layer["transfer_candidates"]) >= 1
    assert layer["transfer_candidate_manifest"]["transfer_is_not_proof"] is True


def test_p27_2_secret_scan():
    assert secret_scan(build_transfer_candidates(_repo())) is True


def test_p27_2_gate_passes():
    assert validate_p27_2_gate(_summary())["ok"] is True
