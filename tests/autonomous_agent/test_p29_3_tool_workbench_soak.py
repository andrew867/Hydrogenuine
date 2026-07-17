"""P29-3 tool workbench soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.redaction import secret_scan
from hg_runtime.tool_mediated_workbench.schemas import SOAK_ITERATION_COUNT
from hg_runtime.tool_mediated_workbench.tool_workbench_mutation_probe import run_tool_workbench_mutation_probes
from hg_runtime.tool_mediated_workbench.tool_workbench_soak import run_tool_workbench_soak
from hg_runtime.tool_mediated_workbench.workbench_gate import validate_p29_3_gate

ROOT = Path(__file__).resolve().parents[2]


# --- Soak --------------------------------------------------------------------

def test_soak_runs_minimum_iterations():
    soak = run_tool_workbench_soak(ROOT)
    assert soak["manifest"]["iteration_count"] >= SOAK_ITERATION_COUNT


def test_soak_all_iterations_match():
    soak = run_tool_workbench_soak(ROOT)
    assert soak["all_iterations_match"] is True


def test_soak_stable_root_is_deterministic():
    soak = run_tool_workbench_soak(ROOT)
    roots = set(soak["stable_hashes"]["stable_roots"])
    assert len(roots) == 1


def test_soak_iteration_records_neutral():
    soak = run_tool_workbench_soak(ROOT)
    for it in soak["iterations"]:
        assert it["mutation_auto_repaired"] is False
        assert it["replay_match_is_not_truth"] is True


# --- Mutation probes ---------------------------------------------------------

def test_mutation_detects_tool_plan():
    probes = run_tool_workbench_mutation_probes(ROOT)
    by_id = {r["probe_id"]: r for r in probes["results"]}
    assert by_id["mutated_tool_plan"]["mutation_detected"] is True


def test_mutation_detects_sandbox():
    probes = run_tool_workbench_mutation_probes(ROOT)
    by_id = {r["probe_id"]: r for r in probes["results"]}
    assert by_id["mutated_sandbox_result"]["mutation_detected"] is True


def test_mutation_detects_refusal_bypass():
    probes = run_tool_workbench_mutation_probes(ROOT)
    by_id = {r["probe_id"]: r for r in probes["results"]}
    assert by_id["refusal_bypass_attempt"]["mutation_detected"] is True


def test_mutation_not_auto_repaired():
    probes = run_tool_workbench_mutation_probes(ROOT)
    for r in probes["results"]:
        assert r["mutation_auto_repaired"] is False


def test_originals_not_mutated():
    probes = run_tool_workbench_mutation_probes(ROOT)
    for r in probes["results"]:
        assert r["original_artifacts_mutated"] is False


# --- Redaction ---------------------------------------------------------------

def test_secret_scan_passes():
    soak = run_tool_workbench_soak(ROOT)
    assert secret_scan(soak) is True


# --- Gate --------------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p29_2_green": True,
        "iteration_count_met": True,
        "stable_hashes_match": True,
        "mutation_detected_tool_plan": True,
        "mutation_detected_sandbox": True,
        "mutation_detected_refusal_bypass": True,
        "mutation_not_auto_repaired": True,
        "originals_not_mutated": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_web_provider": True,
        "no_patch_application": True,
        "no_deletion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_gate_passes():
    assert validate_p29_3_gate(_summary())["ok"] is True


def test_gate_refuses_missing_p29_2():
    assert validate_p29_3_gate(_summary(p29_2_green=False))["ok"] is False


def test_gate_refuses_unstable_hashes():
    assert validate_p29_3_gate(_summary(stable_hashes_match=False))["ok"] is False


def test_gate_refuses_undetected_mutation():
    assert validate_p29_3_gate(_summary(mutation_detected_tool_plan=False))["ok"] is False


def test_gate_refuses_auto_repair():
    assert validate_p29_3_gate(_summary(mutation_not_auto_repaired=False))["ok"] is False
