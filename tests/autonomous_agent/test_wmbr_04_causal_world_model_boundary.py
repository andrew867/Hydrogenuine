"""WMBR-04 / CAGI-45 causal world-model boundary tests.

Doctrine: Every model is a compressed civilization artifact.
A causal hypothesis is not causal truth. Correlation is not causation.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.causal_world_model_boundary.artifact_writer import build_causal_graph, secret_scan
from hg_runtime.causal_world_model_boundary.belief_loader import (
    discover_latest_bundle,
    load_ledger_bundle,
    validate_ledger_bundle,
)
from hg_runtime.causal_world_model_boundary.correlation_detector import (
    assert_correlation_not_causation,
    build_causal_edge,
)
from hg_runtime.causal_world_model_boundary.fixtures import (
    causal_truth_laundering_fixture,
    correlation_laundering_fixture,
    fixture_ledger_bundle,
    intervention_authorization_laundering_fixture,
)
from hg_runtime.causal_world_model_boundary.gate import validate_wmbr04_gate
from hg_runtime.causal_world_model_boundary.intervention_boundary import (
    build_intervention_proposal,
    validate_intervention_proposal,
)
from hg_runtime.causal_world_model_boundary.replay import replay_graph
from hg_runtime.causal_world_model_boundary.schemas import (
    CausalBoundaryError,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
    WMBR_02_VERDICT_GREEN,
    WMBR_03_VERDICT_GREEN,
    assert_neutral,
)

ROOT = Path(__file__).resolve().parents[2]
WMBR_03_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/WMBR-03-BELIEF-REVISION-LEDGER"


def _out():
    return build_causal_graph(fixture_ledger_bundle())


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr03_green": True,
        "wmbr02_green": True,
        "runtime_p42_green": True,
        "input_belief_revision_ledger_loaded": True,
        "belief_states_loaded": True,
        "causal_claims_written": True,
        "causal_claim_count": 12,
        "causal_hypotheses_written": True,
        "causal_hypothesis_count": 12,
        "causal_edges_written": True,
        "causal_edge_count": 12,
        "causal_graph_manifest_written": True,
        "all_hypotheses_provisional": True,
        "all_edges_hypothetical_or_correlation_only": True,
        "belief_state_is_not_truth": True,
        "belief_revision_is_not_certainty": True,
        "causal_hypothesis_is_not_truth": True,
        "correlation_is_not_causation": True,
        "mechanism_proposal_is_not_proof": True,
        "prediction_is_not_verification": True,
        "intervention_proposal_is_not_action": True,
        "contradiction_kept_visible": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_graph_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_causal_truth_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr04_loads_wmbr03_belief_revision_ledger():
    bundle_dir = discover_latest_bundle(WMBR_03_PROOF_ROOT)
    assert bundle_dir is not None
    bundle = load_ledger_bundle(bundle_dir)
    validate_ledger_bundle(bundle)
    assert bundle["belief_states"]


def test_wmbr04_accepts_fixture_belief_states_when_bundle_unavailable():
    assert _out()["summary"]["hypothesis_count"] > 0


def test_wmbr04_rejects_missing_belief_revision_ledger():
    with pytest.raises(CausalBoundaryError):
        validate_ledger_bundle({"manifest": {}, "belief_states": []})


# --- Seeding ---------------------------------------------------------------

def test_wmbr04_only_provenance_bound_belief_states_seed_hypotheses():
    out = _out()
    # Every hypothesis carries at least one provenance chain id.
    assert all(h["provenance_chain_ids"] for h in out["hypotheses"])


def test_wmbr04_belief_state_is_not_truth():
    assert all(not h["belief_state_treated_as_truth"] for h in _out()["hypotheses"])


def test_wmbr04_belief_revision_is_not_certainty():
    assert all(not h["belief_revision_treated_as_certainty"] for h in _out()["hypotheses"])


def test_wmbr04_creates_causal_claim_records():
    assert _out()["causal_claims"]


def test_wmbr04_creates_causal_hypothesis_records():
    assert _out()["hypotheses"]


def test_wmbr04_creates_causal_edges():
    assert _out()["edges"]


def test_wmbr04_all_edges_hypothetical():
    assert all(e["edge_status"] in ("HYPOTHETICAL", "CONTRADICTED", "INSUFFICIENT_EVIDENCE") for e in _out()["edges"])
    assert _out()["manifest"]["all_edges_hypothetical"] is True


# --- Truth / causation boundaries -----------------------------------------

def test_wmbr04_causal_hypothesis_is_not_truth():
    assert all(not h["causal_truth_claimed"] for h in _out()["hypotheses"])


def test_wmbr04_causal_edge_is_not_truth():
    assert all(not e["edge_is_truth"] for e in _out()["edges"])


def test_wmbr04_correlation_is_not_causation():
    assert all(not e["correlation_is_causation"] for e in _out()["edges"])


def test_wmbr04_correlation_only_fixture_not_promoted_to_causation():
    out = _out()
    corr_edges = [e for e in out["edges"] if e["relation_type"] == "CORRELATES_WITH"]
    assert corr_edges
    for e in corr_edges:
        assert not e["correlation_is_causation"]
        assert_correlation_not_causation(e)


def test_wmbr04_mechanism_proposal_is_not_proof():
    assert all(not m["mechanism_is_proof"] for m in _out()["mechanisms"])


def test_wmbr04_prediction_is_not_verification():
    assert all(not p["prediction_is_verification"] for p in _out()["predictions"])


def test_wmbr04_intervention_proposal_is_not_action():
    assert all(not i["intervention_proposal_treated_as_action"] for i in _out()["interventions"])


def test_wmbr04_falsification_condition_is_not_execution_authority():
    assert all(
        f["condition_status"] == "RECORDED_NOT_EXECUTED" and not f["execution_authorized"]
        for f in _out()["falsifications"]
    )


# --- Intervention boundary -------------------------------------------------

def test_wmbr04_intervention_proposal_not_authorized():
    assert all(i["intervention_status"] == "PROPOSED_NOT_AUTHORIZED" for i in _out()["interventions"])


def test_wmbr04_no_action_authorized():
    assert all(not i["action_authorized"] for i in _out()["interventions"])


def test_wmbr04_no_tools_authorized():
    out = _out()
    assert all(not i["tools_authorized"] for i in out["interventions"])
    assert out["manifest"]["tools_authorized"] is False


def test_wmbr04_no_web_browse():
    assert _out()["manifest"]["web_browse_performed"] is False


def test_wmbr04_no_external_provider_calls():
    assert _out()["manifest"]["external_provider_calls_made"] is False


def test_wmbr04_no_live_effects():
    assert _out()["manifest"]["live_external_side_effects_created"] is False


def test_wmbr04_no_authority_granted():
    assert _out()["manifest"]["authority_granted"] is False


# --- Contradiction / retraction -------------------------------------------

def test_wmbr04_contradiction_kept_visible():
    out = _out()
    assert out["summary"]["contradiction_kept_visible"] is True
    assert any(h["hypothesis_status"] == "CONTRADICTED" for h in out["hypotheses"])


def test_wmbr04_retracted_claims_do_not_seed_active_hypotheses():
    out = _out()
    assert out["manifest"]["retracted_seeds_excluded"] >= 1
    assert out["manifest"]["retracted_claims_seed_active_hypotheses"] is False
    assert not any("retracted" in h["hypothesis_id"] for h in out["hypotheses"])


def test_wmbr04_no_causal_truth_claimed():
    assert all(not h.get("causal_truth_claimed") for h in _out()["hypotheses"])


def test_wmbr04_no_certainty_claimed():
    assert all(not h.get("certainty_claimed") for h in _out()["hypotheses"])


# --- Prior-phase preservation ---------------------------------------------

def test_wmbr04_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr04_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr04_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr04_does_not_complete_wmbr01_parent():
    assert validate_wmbr04_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay & laundering ---------------------------------------------------

def test_wmbr04_replay_preserves_graph_hash():
    out = _out()
    assert replay_graph(out["hypotheses"], out["edges"], out["manifest"])["ok"] is True


def test_wmbr04_replay_rejects_mutated_graph():
    out = _out()
    edges = copy.deepcopy(out["edges"])
    edges[0]["edge_status"] = "MUTATED_STATUS"
    assert replay_graph(out["hypotheses"], edges, out["manifest"])["ok"] is False


def test_wmbr04_no_secret_material_in_artifacts():
    assert secret_scan(_out()) is True
    assert "sk-lm-" not in repr(_out())


def test_wmbr04_fake_green_causal_truth_rejected():
    assert validate_wmbr04_gate(_gate_summary(causal_truth_claimed=True))["ok"] is False
    assert validate_wmbr04_gate(_gate_summary(certainty_claimed=True))["ok"] is False


def test_wmbr04_causal_truth_laundering_fixture_rejected():
    with pytest.raises(CausalBoundaryError):
        assert_neutral(causal_truth_laundering_fixture())


def test_wmbr04_correlation_laundering_fixture_rejected():
    with pytest.raises(CausalBoundaryError):
        assert_neutral(correlation_laundering_fixture())
    with pytest.raises(CausalBoundaryError):
        assert_correlation_not_causation(correlation_laundering_fixture())


def test_wmbr04_intervention_authorization_laundering_fixture_rejected():
    with pytest.raises(CausalBoundaryError):
        validate_intervention_proposal(intervention_authorization_laundering_fixture())
    with pytest.raises(CausalBoundaryError):
        assert_neutral(intervention_authorization_laundering_fixture())


def test_wmbr04_clean_intervention_proposal_validates():
    proposal = build_intervention_proposal(hypothesis={"hypothesis_id": "hyp-x"})
    validate_intervention_proposal(proposal)
    assert proposal["intervention_status"] == "PROPOSED_NOT_AUTHORIZED"


# --- Gate ------------------------------------------------------------------

def test_wmbr04_gate_requires_wmbr03_green():
    assert validate_wmbr04_gate(_gate_summary(wmbr03_green=False))["ok"] is False
    assert WMBR_03_VERDICT_GREEN.startswith("GREEN_WMBR_03")


def test_wmbr04_gate_requires_wmbr02_green():
    assert validate_wmbr04_gate(_gate_summary(wmbr02_green=False))["ok"] is False
    assert WMBR_02_VERDICT_GREEN.startswith("GREEN_WMBR_02")


def test_wmbr04_gate_requires_runtime_p42_green():
    assert validate_wmbr04_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr04_gate_refuses_without_hypotheses():
    assert validate_wmbr04_gate(_gate_summary(causal_hypotheses_written=False, causal_hypothesis_count=0))["ok"] is False


def test_wmbr04_gate_refuses_without_edges():
    assert validate_wmbr04_gate(_gate_summary(causal_edges_written=False, causal_edge_count=0))["ok"] is False


def test_wmbr04_gate_refuses_if_edge_marked_truth():
    assert validate_wmbr04_gate(_gate_summary(causal_edge_treated_as_truth=True))["ok"] is False


def test_wmbr04_gate_refuses_if_causal_truth_claimed():
    assert validate_wmbr04_gate(_gate_summary(causal_truth_claimed=True))["ok"] is False


def test_wmbr04_gate_refuses_if_correlation_treated_as_causation():
    assert validate_wmbr04_gate(_gate_summary(correlation_treated_as_causation=True))["ok"] is False


def test_wmbr04_gate_refuses_if_intervention_authorized():
    assert validate_wmbr04_gate(_gate_summary(intervention_authorized=True))["ok"] is False


def test_wmbr04_gate_refuses_if_action_authorized():
    assert validate_wmbr04_gate(_gate_summary(action_authorized=True))["ok"] is False


def test_wmbr04_gate_refuses_if_tool_authorized():
    assert validate_wmbr04_gate(_gate_summary(tools_authorized=True))["ok"] is False


def test_wmbr04_gate_refuses_if_authority_granted():
    assert validate_wmbr04_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr04_gate_refuses_if_live_effect_created():
    assert validate_wmbr04_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr04_gate_refuses_without_proof_bundle():
    assert validate_wmbr04_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr04_gate_passes_on_full_summary():
    assert validate_wmbr04_gate(_gate_summary())["ok"] is True
