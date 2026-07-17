"""DTX-4 document text soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_soak_runner import run_dtx_document_soak_with_mutations
from hg_runtime.document_text_exchange.gate import validate_dtx4_gate
from hg_runtime.document_text_exchange.schemas import MUTATION_PROBE_TYPES, SOAK_ITERATION_COUNT

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return run_dtx_document_soak_with_mutations(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DTX_4_DOCUMENT_TEXT_SOAK",
        "dib_consolidation_green": True,
        "dtx3_green": True,
        "iteration_count_met": True,
        "all_iterations_match": True,
        "stable_hashes_written": True,
        "mutation_probes_written": True,
        "mutation_results_written": True,
        "mismatches_detected": True,
        "soak_not_truth": True,
        "replay_not_truth": True,
        "mutation_not_repair": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dtx4_runs_five_iterations():
    assert len(_layer()["dtx_soak_iterations"]) == SOAK_ITERATION_COUNT


def test_dtx4_all_iterations_match():
    layer = _layer()
    assert all(row["replay_match"] for row in layer["dtx_soak_iterations"])


def test_dtx4_mutation_probes_exercised():
    layer = _layer()
    assert len(layer["dtx_mutation_probes"]) == len(MUTATION_PROBE_TYPES)


def test_dtx4_detects_all_mismatches():
    assert _layer()["all_mismatches_detected"] is True


def test_dtx4_mutation_not_repair():
    layer = _layer()
    assert all(not row["mutation_auto_repaired"] for row in layer["dtx_mutation_results"])


def test_dtx4_gate_passes():
    assert validate_dtx4_gate(_summary())["ok"] is True
