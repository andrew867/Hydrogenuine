"""OES-2 mutation replay mismatch tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_soak.gate import validate_oes2_gate
from hg_runtime.operator_evidence_soak.iteration_runner import run_repeated_corpus_soak
from hg_runtime.operator_evidence_soak.mutation_probe import build_mutation_layer
from hg_runtime.operator_evidence_soak.replay_mismatch_detector import run_mutation_replay_detection
from hg_runtime.operator_evidence_soak.schemas import MUTATION_PROBE_TYPES

ROOT = Path(__file__).resolve().parents[2]


def _baseline():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    return mutation["baseline"]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OES_2_MUTATION_REPLAY_MISMATCH_DETECTOR",
        "oec_consolidation_green": True,
        "oes1_green": True,
        "all_probe_types_exercised": True,
        "probes_written": True,
        "results_written": True,
        "mismatches_detected": True,
        "mutation_not_repair": True,
        "mutation_not_deletion": True,
        "mutation_not_patch": True,
        "original_preserved": True,
        "no_live_effects": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_oes2_exercises_all_probe_types():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    assert len(mutation["probes"]) == len(MUTATION_PROBE_TYPES)


def test_oes2_detects_all_mismatches():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    layer = run_mutation_replay_detection(baseline_layer=mutation["baseline"], probes=mutation["probes"])
    assert layer["all_mismatches_detected"] is True
    assert all(row["mismatch_detected"] for row in layer["mutation_results"])


def test_oes2_preserves_original_artifacts():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    baseline_hash = mutation["baseline"]["stable_hash"]
    run_mutation_replay_detection(baseline_layer=mutation["baseline"], probes=mutation["probes"])
    assert mutation["baseline"]["stable_hash"] == baseline_hash


def test_oes2_mutation_not_repair():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    layer = run_mutation_replay_detection(baseline_layer=mutation["baseline"], probes=mutation["probes"])
    assert all(not row["mutation_auto_repaired"] for row in layer["mutation_results"])


def test_oes2_gate_passes():
    assert validate_oes2_gate(_summary())["ok"] is True
