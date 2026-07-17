"""OES-1 repeated corpus replay soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_soak.gate import validate_oes1_gate
from hg_runtime.operator_evidence_soak.iteration_runner import run_repeated_corpus_soak
from hg_runtime.operator_evidence_soak.schemas import SOAK_ITERATION_COUNT

ROOT = Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OES_1_REPEATED_CORPUS_REPLAY_SOAK",
        "oec_consolidation_green": True,
        "oes0_green": True,
        "iteration_count_met": True,
        "all_iterations_match": True,
        "stable_hashes_written": True,
        "explicit_corpus_manifest_only": True,
        "old_proof_not_mutated": True,
        "replay_not_truth": True,
        "stable_hash_not_correctness": True,
        "no_belief_promotion": True,
        "no_live_effects": True,
        "no_web_or_provider": True,
        "no_arbitrary_ingestion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_oes1_runs_five_iterations():
    layer = run_repeated_corpus_soak(ROOT)
    assert len(layer["soak_iterations"]) == SOAK_ITERATION_COUNT


def test_oes1_stable_hashes_match():
    layer = run_repeated_corpus_soak(ROOT)
    expected = layer["stable_hashes"]["expected_hash"]
    assert all(row["stable_hash"] == expected for row in layer["soak_iterations"])


def test_oes1_replay_all_match():
    layer = run_repeated_corpus_soak(ROOT)
    assert layer["soak_replay_result"]["all_iterations_match"] is True


def test_oes1_uses_explicit_corpus_manifest():
    layer = run_repeated_corpus_soak(ROOT)
    assert layer["soak_manifest"]["explicit_corpus_manifest_only"] is True
    assert layer["soak_manifest"]["corpus_manifest_ref"]


def test_oes1_not_truth_boundaries():
    layer = run_repeated_corpus_soak(ROOT)
    assert all(not row["replay_match_treated_as_truth"] for row in layer["soak_iterations"])
    assert layer["soak_replay_result"]["determinism_treated_as_correctness"] is False


def test_oes1_gate_passes():
    assert validate_oes1_gate(_summary())["ok"] is True
