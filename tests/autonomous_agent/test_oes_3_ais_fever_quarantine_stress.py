"""OES-3 AIS fever and quarantine stress tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_soak.ais_soak_integration import run_ais_soak_stress
from hg_runtime.operator_evidence_soak.gate import validate_oes3_gate
from hg_runtime.operator_evidence_soak.iteration_runner import run_repeated_corpus_soak
from hg_runtime.operator_evidence_soak.mutation_probe import build_mutation_layer
from hg_runtime.operator_evidence_soak.replay_mismatch_detector import run_mutation_replay_detection

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    soak = run_repeated_corpus_soak(ROOT)
    mutation = build_mutation_layer(soak["baseline_layer"])
    mutation_layer = run_mutation_replay_detection(baseline_layer=mutation["baseline"], probes=mutation["probes"])
    return run_ais_soak_stress(mutation_layer=mutation_layer, soak_replay=soak)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OES_3_AIS_FEVER_QUARANTINE_STRESS",
        "oec_consolidation_green": True,
        "oes2_green": True,
        "health_findings_written": True,
        "fever_reports_written": True,
        "quarantine_candidates_written": True,
        "security_findings_written": True,
        "patch_hygiene_tasks_written": True,
        "fever_restricts_never_unlocks": True,
        "quarantine_not_deletion": True,
        "security_defensive_only": True,
        "patch_hygiene_not_patch": True,
        "mutation_not_repair": True,
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


def test_oes3_writes_health_findings():
    layer = _layer()
    assert layer["soak_health_findings"]


def test_oes3_fever_restricts_never_unlocks():
    layer = _layer()
    fever = layer["soak_fever_reports"][0]
    assert fever["fever_unlocks_action"] is False


def test_oes3_quarantine_is_not_deletion():
    layer = _layer()
    assert all(not row["quarantine_candidate_is_deletion"] for row in layer["soak_quarantine_candidates"])


def test_oes3_patch_hygiene_not_patch():
    layer = _layer()
    assert all(not row["patch_hygiene_task_is_patch"] for row in layer["soak_patch_hygiene_tasks"])


def test_oes3_security_defensive_only():
    layer = _layer()
    assert all(row["security_finding_defensive_only"] for row in layer["soak_security_findings"])


def test_oes3_gate_passes():
    assert validate_oes3_gate(_summary())["ok"] is True
