"""P28-3 domain pack soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_pack_mutation_probe import run_domain_pack_mutation_probes
from hg_runtime.domain_pack_runtime.domain_pack_soak import run_domain_pack_soak
from hg_runtime.domain_pack_runtime.gate import validate_p28_3_gate
from hg_runtime.domain_pack_runtime.schemas import SOAK_ITERATION_COUNT


def _repo():
    return Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P28_3_DOMAIN_PACK_SOAK",
        "p28_2_green": True,
        "iteration_count_met": True,
        "all_iterations_match": True,
        "stable_hashes_written": True,
        "mutation_probes_written": True,
        "mismatches_detected": True,
        "mutation_not_repair": True,
        "original_artifacts_not_mutated": True,
        "soak_not_proof": True,
        "replay_not_truth": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p28_3_soak_iterations():
    soak = run_domain_pack_soak(_repo(), iterations=SOAK_ITERATION_COUNT)
    assert soak["manifest"]["iteration_count"] == SOAK_ITERATION_COUNT
    assert soak["all_iterations_match"] is True


def test_p28_3_mutation_probes_detect():
    mutation = run_domain_pack_mutation_probes(_repo())
    assert all(row["mutation_detected"] for row in mutation["results"])


def test_p28_3_gate_passes():
    assert validate_p28_3_gate(_summary())["ok"] is True
