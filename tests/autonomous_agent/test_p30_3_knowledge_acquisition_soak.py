"""P30-3 knowledge acquisition soak tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p30_3_knowledge_acquisition_soak_gate.py"
_spec = importlib.util.spec_from_file_location("p30_3_gate", _GATE_PATH)
p30_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p30_gate)

ROOT = Path(__file__).resolve().parents[2]

from hg_runtime.knowledge_acquisition_loop.acquisition_loop import build_acquisition_loop_layer
from hg_runtime.knowledge_acquisition_loop.knowledge_acquisition_mutation_probe import (
    probe_mutated_source,
    probe_mutated_task,
    probe_truth_promotion_attempt,
    run_mutation_probes,
)
from hg_runtime.knowledge_acquisition_loop.knowledge_acquisition_soak import (
    run_knowledge_acquisition_soak,
    stable_run_material,
)
from hg_runtime.knowledge_acquisition_loop.knowledge_gate import validate_p30_3_gate
from hg_runtime.knowledge_acquisition_loop.schemas import SOAK_ITERATION_COUNT


# --- Gate --------------------------------------------------------------------

def test_gate_green():
    code, summary = p30_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P30_3_KNOWLEDGE_ACQUISITION_SOAK"
    assert summary["ok"] is True
    assert summary["failures"] == []


# --- Soak --------------------------------------------------------------------

def test_soak_iteration_count():
    soak = run_knowledge_acquisition_soak(ROOT)
    assert soak["iteration_count"] == SOAK_ITERATION_COUNT
    assert soak["iteration_count"] >= 5


def test_soak_all_stable():
    soak = run_knowledge_acquisition_soak(ROOT)
    assert soak["all_stable"] is True


def test_soak_iterations_match():
    soak = run_knowledge_acquisition_soak(ROOT)
    assert all(it["matches_baseline"] for it in soak["iterations"])


def test_stable_run_material():
    layer = build_acquisition_loop_layer(ROOT)
    material = stable_run_material(layer)
    assert "manifest_hash" in material
    assert "result_hashes" in material
    assert "refusal_hashes" in material


# --- Mutation probes ---------------------------------------------------------

def test_probe_mutated_task():
    layer = build_acquisition_loop_layer(ROOT)
    result = probe_mutated_task(layer)
    assert result["detected"] is True


def test_probe_mutated_source():
    layer = build_acquisition_loop_layer(ROOT)
    result = probe_mutated_source(layer)
    assert result["detected"] is True


def test_probe_truth_promotion():
    layer = build_acquisition_loop_layer(ROOT)
    result = probe_truth_promotion_attempt(layer)
    assert result["detected"] is True


def test_run_mutation_probes():
    layer = build_acquisition_loop_layer(ROOT)
    probes = run_mutation_probes(layer)
    assert probes["mutated_task"]["detected"] is True
    assert probes["mutated_source"]["detected"] is True
    assert probes["truth_promotion"]["detected"] is True
    assert probes["originals_not_mutated"] is True
    assert probes["mutation_not_auto_repaired"] is True


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p30_2_green": True,
        "iteration_count_met": True,
        "stable_hashes_match": True,
        "mutation_detected_task": True,
        "mutation_detected_source": True,
        "mutation_detected_truth_promotion": True,
        "mutation_not_auto_repaired": True,
        "originals_not_mutated": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert validate_p30_3_gate(_summary())["ok"] is True


def test_validator_fails_no_p30_2():
    assert validate_p30_3_gate(_summary(p30_2_green=False))["ok"] is False


def test_validator_fails_unstable():
    assert validate_p30_3_gate(_summary(stable_hashes_match=False))["ok"] is False


def test_validator_fails_missing_mutation():
    assert validate_p30_3_gate(_summary(mutation_detected_task=False))["ok"] is False


def test_validator_fails_forbidden():
    assert validate_p30_3_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False
