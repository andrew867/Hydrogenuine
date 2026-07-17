"""WMBR-01A / CAGI-42A cross-model perspective matrix tests.

Doctrine: Every model is a compressed civilization artifact.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.cross_model_perspective.artifact_writer import build_artifacts, secret_scan
from hg_runtime.cross_model_perspective.fixtures import fixture_prompts, fixture_receipts
from hg_runtime.cross_model_perspective.gate import validate_wmbr01a_gate
from hg_runtime.cross_model_perspective.receipt_loader import (
    discover_latest_bundle,
    load_from_bundle,
    normalize_receipts,
)
from hg_runtime.cross_model_perspective.replay import replay_matrices
from hg_runtime.cross_model_perspective.schemas import (
    CrossModelPerspectiveError,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
)

ROOT = Path(__file__).resolve().parents[2]
OUTER_ROOT = ROOT.parent
P42_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/PHASE-42-PROVIDER-PORTABILITY"
CROSSWALK_PATH = OUTER_ROOT / "docs/planning/agi/candidate_agi/02_RUNTIME_IMPLEMENTATION_CROSSWALK.md"

PROMPTS_META = {p["prompt_id"]: p for p in fixture_prompts()}


def _bundle():
    return build_artifacts(fixture_receipts(), PROMPTS_META)


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "runtime_p42_green": True,
        "crosswalk_exists": True,
        "runtime_p42_declared_not_cagi42": True,
        "wmbr01a_declared_not_wmbr01": True,
        "input_receipts_loaded": True,
        "receipt_count": 20,
        "participant_count": 3,
        "perspective_matrix_written": True,
        "divergence_matrix_written": True,
        "refusal_patterns_written": True,
        "omission_patterns_written": True,
        "framing_signatures_written": True,
        "moral_consensus_matrix_written": True,
        "evidence_gap_tasks_written": True,
        "every_matrix_cell_links_to_receipt": True,
        "consensus_is_explicitly_non_truth": True,
        "divergence_is_explicitly_non_evidence": True,
        "refusal_is_explicitly_non_authority": True,
        "willingness_is_explicitly_non_permission": True,
        "moral_consensus_is_explicitly_non_authority": True,
        "evidence_gap_tasks_are_not_actions": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_matrix_hashes": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_truth_claim_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr01a_loads_runtime_p42_receipts():
    bundle_dir = discover_latest_bundle(P42_PROOF_ROOT)
    assert bundle_dir is not None
    receipts = load_from_bundle(bundle_dir)
    assert receipts
    normalized = normalize_receipts(receipts)
    assert all(n["receipt_id"] for n in normalized)


def test_wmbr01a_accepts_fixture_receipts_when_bundle_unavailable():
    assert _bundle()["summary"]["receipt_count"] == len(fixture_receipts())


def test_wmbr01a_rejects_missing_receipts():
    with pytest.raises(CrossModelPerspectiveError):
        normalize_receipts([])


# --- Perspective matrix ----------------------------------------------------

def test_wmbr01a_builds_perspective_matrix():
    matrix = _bundle()["perspective_matrix"]
    assert matrix["cell_count"] > 0
    assert matrix["rows"] and matrix["columns"]


def test_wmbr01a_every_matrix_cell_links_to_receipt():
    matrix = _bundle()["perspective_matrix"]
    assert matrix["every_cell_links_to_receipt"] is True
    assert all(c["receipt_id"] and c["links_to_receipt"] for c in matrix["cells"])


# --- Divergence ------------------------------------------------------------

def test_wmbr01a_builds_divergence_matrix():
    assert _bundle()["divergence_matrix"]["record_count"] > 0


def test_wmbr01a_records_refusal_divergence():
    types = {r["divergence_type"] for r in _bundle()["divergence_matrix"]["records"]}
    assert "refusal_divergence" in types


def test_wmbr01a_refusal_is_not_authority():
    assert all(not p["refusal_is_authority"] for p in _bundle()["refusal_patterns"])


def test_wmbr01a_willingness_is_not_permission():
    assert all(not t["authorizes_actions"] for t in _bundle()["evidence_gap_tasks"])
    assert _bundle()["summary"]["model_willingness_treated_as_permission"] is False


def test_wmbr01a_consensus_is_not_truth():
    assert _bundle()["summary"]["model_consensus_treated_as_truth"] is False
    assert _bundle()["perspective_matrix"]["consensus_is_truth"] is False


def test_wmbr01a_divergence_is_not_evidence():
    dm = _bundle()["divergence_matrix"]
    assert dm["divergence_is_not_evidence"] is True
    assert all(not r["is_evidence"] for r in dm["records"])


def test_wmbr01a_omission_is_not_proof_of_intent():
    omissions = _bundle()["omission_patterns"]
    assert omissions
    assert all(not o["interpreted_as_intent"] and not o["is_proof_of_intent"] for o in omissions)


def test_wmbr01a_framing_signature_is_descriptive_only():
    framing = _bundle()["framing_signatures"]
    assert framing
    assert all(f["descriptive_only"] and not f["framing_is_authority"] for f in framing)


def test_wmbr01a_moral_consensus_is_not_authority():
    matrix = _bundle()["moral_consensus_matrix"]
    assert matrix["shared_principle_count"] > 0
    assert matrix["moral_consensus_is_authority"] is False


def test_wmbr01a_moral_conflict_recorded_without_adjudication():
    conflicts = _bundle()["moral_conflict_records"]
    assert conflicts
    assert all(not c["adjudicated"] for c in conflicts)


# --- Evidence gap tasks ----------------------------------------------------

def test_wmbr01a_evidence_gap_task_created_for_unsourced_consensus():
    kinds = {t["task_kind"] for t in _bundle()["evidence_gap_tasks"]}
    assert "unsourced_consensus" in kinds


def test_wmbr01a_evidence_gap_task_is_not_action():
    assert all(not t["is_action"] for t in _bundle()["evidence_gap_tasks"])


def test_wmbr01a_evidence_gap_task_does_not_authorize_tools():
    assert all(not t["authorizes_tools"] for t in _bundle()["evidence_gap_tasks"])


def test_wmbr01a_generic_slop_recorded_not_ready():
    bundle = _bundle()
    generic_cells = [c for c in bundle["perspective_matrix"]["cells"] if c["specificity_class"] == "GENERIC"]
    assert generic_cells
    kinds = {t["task_kind"] for t in bundle["evidence_gap_tasks"]}
    assert "generic_low_specificity" in kinds


# --- Boundaries ------------------------------------------------------------

def test_wmbr01a_no_external_provider_calls():
    assert _bundle()["summary"]["external_provider_calls_made"] is False


def test_wmbr01a_no_live_effects():
    assert _bundle()["summary"]["live_external_side_effects_created"] is False


def test_wmbr01a_no_authority_granted():
    assert _bundle()["summary"]["authority_granted"] is False


def test_wmbr01a_no_tools_authorized():
    assert _bundle()["summary"]["tools_authorized"] is False


def test_wmbr01a_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr01a_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr01a_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr01a_runtime_p42_not_cagi42():
    text = CROSSWALK_PATH.read_text(encoding="utf-8")
    assert "Runtime P42 Provider Portability does not complete CAGI-42 Causal World Model" in text


def test_wmbr01a_does_not_complete_wmbr01_causal_world_model():
    assert validate_wmbr01a_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay ----------------------------------------------------------------

def test_wmbr01a_replay_preserves_matrix_hashes():
    bundle = _bundle()
    assert replay_matrices(bundle["perspective_matrix"], bundle["divergence_matrix"])["ok"] is True


def test_wmbr01a_replay_rejects_mutated_matrix():
    bundle = _bundle()
    pm = copy.deepcopy(bundle["perspective_matrix"])
    pm["cells"][0]["included_claim_tags"] = ["claim:mutated"]
    assert replay_matrices(pm, bundle["divergence_matrix"])["ok"] is False


def test_wmbr01a_no_secret_material_in_artifacts():
    assert secret_scan(_bundle()) is True
    assert "sk-lm-" not in repr(_bundle())


def test_wmbr01a_fake_green_truth_claim_rejected():
    assert validate_wmbr01a_gate(_gate_summary(model_consensus_treated_as_truth=True))["ok"] is False


# --- Gate ------------------------------------------------------------------

def test_wmbr01a_gate_requires_runtime_p42_green():
    assert validate_wmbr01a_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr01a_gate_requires_crosswalk():
    assert validate_wmbr01a_gate(_gate_summary(crosswalk_exists=False))["ok"] is False


def test_wmbr01a_gate_refuses_without_perspective_matrix():
    assert validate_wmbr01a_gate(_gate_summary(perspective_matrix_written=False))["ok"] is False


def test_wmbr01a_gate_refuses_if_consensus_marked_truth():
    assert validate_wmbr01a_gate(_gate_summary(model_consensus_treated_as_truth=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_refusal_grants_authority():
    assert validate_wmbr01a_gate(_gate_summary(model_refusal_treated_as_authority=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_willingness_grants_permission():
    assert validate_wmbr01a_gate(_gate_summary(model_willingness_treated_as_permission=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_moral_consensus_grants_authority():
    assert validate_wmbr01a_gate(_gate_summary(moral_consensus_treated_as_authority=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_external_provider_called():
    assert validate_wmbr01a_gate(_gate_summary(external_provider_calls_made=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_authority_granted():
    assert validate_wmbr01a_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr01a_gate_refuses_if_live_effect_created():
    assert validate_wmbr01a_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr01a_gate_refuses_without_proof_bundle():
    assert validate_wmbr01a_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr01a_gate_requires_crosswalk_runtime_p42_not_cagi42():
    assert validate_wmbr01a_gate(_gate_summary(runtime_p42_declared_not_cagi42=False))["ok"] is False


def test_wmbr01a_gate_passes_on_full_summary():
    assert validate_wmbr01a_gate(_gate_summary())["ok"] is True
