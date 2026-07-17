"""P30-1 acquisition task builder tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p30_1_acquisition_task_builder_gate.py"
_spec = importlib.util.spec_from_file_location("p30_1_gate", _GATE_PATH)
p30_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p30_gate)

ROOT = Path(__file__).resolve().parents[2]

from hg_runtime.knowledge_acquisition_loop.acquisition_task_builder import (
    build_acquisition_task_layer,
    replay_acquisition_task_layer,
)
from hg_runtime.knowledge_acquisition_loop.knowledge_gate import validate_p30_1_gate
from hg_runtime.knowledge_acquisition_loop.workbench_gap_mapper import (
    map_evidence_gaps_to_candidates,
    map_workbench_gaps_to_candidates,
)


# --- Gate --------------------------------------------------------------------

def test_gate_green():
    code, summary = p30_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P30_1_ACQUISITION_TASK_BUILDER"
    assert summary["ok"] is True
    assert summary["failures"] == []


# --- Workbench gap mapper ----------------------------------------------------

def test_workbench_gaps_mapped():
    result = map_workbench_gaps_to_candidates(ROOT)
    assert "workbench_gap_candidates" in result
    assert isinstance(result["workbench_gap_candidates"], list)


def test_evidence_gaps_mapped():
    candidates = map_evidence_gaps_to_candidates(ROOT)
    assert isinstance(candidates, list)
    assert len(candidates) > 0


# --- Task builder layer ------------------------------------------------------

def test_layer_builds():
    layer = build_acquisition_task_layer(ROOT)
    assert "policy" in layer
    assert "candidates" in layer
    assert "sources" in layer
    assert "tasks" in layer
    assert "manifest" in layer


def test_layer_has_tasks():
    layer = build_acquisition_task_layer(ROOT)
    assert len(layer["tasks"]) > 0


def test_all_tasks_fixture_only():
    layer = build_acquisition_task_layer(ROOT)
    assert all(t["fixture_only"] for t in layer["tasks"])


def test_all_tasks_sandbox_only():
    layer = build_acquisition_task_layer(ROOT)
    assert all(t["sandbox_only"] for t in layer["tasks"])


def test_all_tasks_not_action():
    layer = build_acquisition_task_layer(ROOT)
    assert all(t["acquisition_task_is_not_action"] for t in layer["tasks"])


def test_candidate_count_matches():
    layer = build_acquisition_task_layer(ROOT)
    assert len(layer["candidates"]) == layer["manifest"]["candidate_count"]


def test_task_count_matches():
    layer = build_acquisition_task_layer(ROOT)
    assert len(layer["tasks"]) == layer["manifest"]["task_count"]


# --- Replay ------------------------------------------------------------------

def test_replay_deterministic():
    layer = build_acquisition_task_layer(ROOT)
    replay = replay_acquisition_task_layer(ROOT, layer["manifest"]["manifest_hash"])
    assert replay["replay_preserves_manifest_hash"] is True


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p30_0_green": True,
        "p29_consolidation_green": True,
        "tasks_built": True,
        "tasks_fixture_only": True,
        "tasks_sandbox_only": True,
        "task_not_action": True,
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
    assert validate_p30_1_gate(_summary())["ok"] is True


def test_validator_fails_no_p30_0():
    assert validate_p30_1_gate(_summary(p30_0_green=False))["ok"] is False


def test_validator_fails_no_p29():
    assert validate_p30_1_gate(_summary(p29_consolidation_green=False))["ok"] is False


def test_validator_fails_no_tasks():
    assert validate_p30_1_gate(_summary(tasks_built=False))["ok"] is False


def test_validator_fails_forbidden():
    assert validate_p30_1_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False


def test_validator_fails_live_web():
    assert validate_p30_1_gate(_summary(web_browse_performed=True))["ok"] is False
