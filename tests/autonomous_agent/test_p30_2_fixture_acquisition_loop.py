"""P30-2 fixture-only acquisition loop tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p30_2_fixture_acquisition_loop_gate.py"
_spec = importlib.util.spec_from_file_location("p30_2_gate", _GATE_PATH)
p30_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p30_gate)

ROOT = Path(__file__).resolve().parents[2]

from hg_runtime.knowledge_acquisition_loop.acquisition_loop import (
    build_acquisition_loop_layer,
    replay_acquisition_loop,
)
from hg_runtime.knowledge_acquisition_loop.acquisition_loop_simulator import simulate_acquisition_loop
from hg_runtime.knowledge_acquisition_loop.acquisition_refusal import build_acquisition_refusal
from hg_runtime.knowledge_acquisition_loop.knowledge_gate import validate_p30_2_gate
from hg_runtime.knowledge_acquisition_loop.schemas import REFUSAL_REASONS, KnowledgeAcquisitionBoundaryError


# --- Gate --------------------------------------------------------------------

def test_gate_green():
    code, summary = p30_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P30_2_FIXTURE_ACQUISITION_LOOP"
    assert summary["ok"] is True
    assert summary["failures"] == []


# --- Refusal builder ---------------------------------------------------------

def test_refusal_builds():
    r = build_acquisition_refusal(
        refusal_id="ref-1", task_id="t-1",
        refusal_reason="live_web_acquisition",
        description="Refused live web",
    )
    assert r["record_type"] == "acquisition_refusal_v1"
    assert r["refusal_reason"] == "live_web_acquisition"


def test_refusal_rejects_unknown():
    with pytest.raises(KnowledgeAcquisitionBoundaryError):
        build_acquisition_refusal(
            refusal_id="ref-1", task_id="t-1",
            refusal_reason="UNKNOWN",
            description="test",
        )


# --- Simulator ---------------------------------------------------------------

def test_simulator_produces_results():
    from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import build_acquisition_task_layer
    layer = build_acquisition_task_layer(ROOT)
    sim = simulate_acquisition_loop(layer["tasks"], layer["sources"])
    assert len(sim["results"]) > 0


def test_simulator_produces_refusals():
    from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import build_acquisition_task_layer
    layer = build_acquisition_task_layer(ROOT)
    sim = simulate_acquisition_loop(layer["tasks"], layer["sources"])
    assert len(sim["refusals"]) > 0


def test_simulator_all_refusal_reasons_covered():
    from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import build_acquisition_task_layer
    layer = build_acquisition_task_layer(ROOT)
    sim = simulate_acquisition_loop(layer["tasks"], layer["sources"])
    assert sim["all_refusal_reasons_covered"] is True
    assert set(sim["covered_refusal_reasons"]) == REFUSAL_REASONS


def test_simulator_has_operator_reviews():
    from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import build_acquisition_task_layer
    layer = build_acquisition_task_layer(ROOT)
    sim = simulate_acquisition_loop(layer["tasks"], layer["sources"])
    assert len(sim["operator_reviews"]) > 0


# --- Loop layer --------------------------------------------------------------

def test_loop_layer_builds():
    layer = build_acquisition_loop_layer(ROOT)
    assert "results" in layer
    assert "refusals" in layer
    assert "operator_reviews" in layer
    assert "manifest" in layer


def test_loop_all_refusal_reasons():
    layer = build_acquisition_loop_layer(ROOT)
    assert layer["manifest"]["all_refusal_reasons_covered"] is True


def test_loop_results_not_belief():
    layer = build_acquisition_loop_layer(ROOT)
    for r in layer["results"]:
        assert r["acquisition_result_is_not_belief"] is True
        assert r["acquired_claim_is_not_truth"] is True


# --- Replay ------------------------------------------------------------------

def test_replay_deterministic():
    layer = build_acquisition_loop_layer(ROOT)
    replay = replay_acquisition_loop(ROOT, layer["manifest"]["manifest_hash"])
    assert replay["replay_preserves_manifest_hash"] is True


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p30_1_green": True,
        "results_produced": True,
        "refusals_produced": True,
        "all_refusal_reasons_covered": True,
        "unsourced_normalized": True,
        "operator_review_created": True,
        "acquired_claim_not_truth": True,
        "acquisition_result_not_belief": True,
        "no_live_web": True,
        "no_external_provider": True,
        "no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
        "no_auto_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert validate_p30_2_gate(_summary())["ok"] is True


def test_validator_fails_no_p30_1():
    assert validate_p30_2_gate(_summary(p30_1_green=False))["ok"] is False


def test_validator_fails_no_refusals():
    assert validate_p30_2_gate(_summary(refusals_produced=False))["ok"] is False


def test_validator_fails_incomplete_refusal_reasons():
    assert validate_p30_2_gate(_summary(all_refusal_reasons_covered=False))["ok"] is False


def test_validator_fails_forbidden():
    assert validate_p30_2_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False
