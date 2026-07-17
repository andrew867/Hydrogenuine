"""P26-4 recall replay soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.gate import validate_p26_4_gate
from hg_runtime.experience_ledger.p26_mutation_probe import run_mutation_probes
from hg_runtime.experience_ledger.p26_recall_soak import run_recall_soak


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_4_RECALL_REPLAY_SOAK",
        "soak_iterations_written": True,
        "at_least_5_iterations": True,
        "stable_hashes_written": True,
        "stable_hashes_match_across_iterations": True,
        "timestamp_proof_path_noise_excluded": True,
        "memory_mutation_detected": True,
        "provenance_mutation_detected": True,
        "promotion_decision_mutation_detected": True,
        "mutation_not_auto_repaired": True,
        "original_artifacts_not_mutated": True,
        "replay_stable": True,
        "memory_is_not_truth": True,
        "recall_is_not_authority": True,
        "promotion_request_is_not_promotion": True,
        "no_belief_promotion": True,
        "no_orp_bypass": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_4_runs_5_deterministic_iterations():
    soak = run_recall_soak(Path.cwd(), iterations=5)
    assert len(soak["iterations"]) == 5
    assert soak["manifest"]["all_iterations_match"] is True


def test_p26_4_stable_hashes_match_across_clean_iterations():
    stable_hashes = run_recall_soak(Path.cwd(), iterations=5)["stable_hashes"]
    assert len(set(stable_hashes["stable_roots"])) == 1


def test_p26_4_timestamp_proof_path_noise_excluded():
    assert run_recall_soak(Path.cwd(), iterations=1)["stable_hashes"]["timestamp_proof_path_noise_excluded"] is True


def test_p26_4_mutation_probes_detect_all_required_changes():
    results = {r["probe_id"]: r for r in run_mutation_probes(Path.cwd())["results"]}
    assert results["memory_record_mutation"]["mutation_detected"] is True
    assert results["provenance_pointer_mutation"]["mutation_detected"] is True
    assert results["promotion_decision_mutation"]["mutation_detected"] is True


def test_p26_4_mutation_is_not_auto_repaired_and_originals_not_mutated():
    results = run_mutation_probes(Path.cwd())["results"]
    assert all(not result["mutation_auto_repair_performed"] for result in results)
    assert all(not result["original_artifacts_mutated"] for result in results)


def test_p26_4_replay_stable_and_boundaries_preserved():
    soak = run_recall_soak(Path.cwd(), iterations=5)
    assert soak["manifest"]["all_iterations_match"] is True
    assert soak["manifest"]["phase19_yellow_preserved"] is True
    assert soak["manifest"]["phase24_infrastructure_only_preserved"] is True


def test_p26_4_memory_not_truth_recall_not_authority_request_not_promotion():
    iteration = run_recall_soak(Path.cwd(), iterations=1)["iterations"][0]
    assert iteration["memory_treated_as_truth"] is False
    assert iteration["recall_treated_as_authority"] is False
    assert iteration["promotion_request_is_promotion"] is False


def test_p26_4_no_belief_promotion_or_orp_bypass():
    iteration = run_recall_soak(Path.cwd(), iterations=1)["iterations"][0]
    assert iteration["belief_promoted"] is False
    assert iteration["orp_bypassed"] is False


def test_p26_4_gate_accepts_green_summary():
    assert validate_p26_4_gate(_summary())["ok"] is True


def test_p26_4_gate_rejects_false_green_boundaries():
    assert validate_p26_4_gate(_summary(memory_treated_as_truth=True))["ok"] is False
    assert validate_p26_4_gate(_summary(recall_treated_as_authority=True))["ok"] is False
    assert validate_p26_4_gate(_summary(promotion_request_auto_applied=True))["ok"] is False
