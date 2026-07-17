"""LEB local evidence bridge consolidation tests."""

from __future__ import annotations

from scripts.evals.autonomous_agent_leb_consolidation_gate import build_consolidation, run_gate


def test_leb_consolidation_lists_leb0_through_leb3():
    out = build_consolidation()
    assert [phase["phase"] for phase in out["phase_index"]] == ["LEB-0", "LEB-1", "LEB-2", "LEB-3"]


def test_leb_consolidation_records_proof_bundle_paths():
    out = build_consolidation()
    assert all(phase["proof_bundle"] for phase in out["phase_index"])


def test_leb_consolidation_records_report_paths():
    out = build_consolidation()
    assert all(phase["report_exists"] for phase in out["phase_index"])


def test_leb_consolidation_records_green_gate_verdicts():
    out = build_consolidation()
    assert all(phase["gate_verdict"] == phase["verdict"] for phase in out["phase_index"])


def test_leb_consolidation_preserves_local_only_boundaries():
    out = build_consolidation()
    boundary = out["boundary_matrix"]
    assert boundary["local_only"] is True
    assert boundary["web_browse_performed"] is False
    assert boundary["external_provider_calls_made"] is False


def test_leb_consolidation_no_truth_authority_or_auto_promotion():
    out = build_consolidation()
    boundary = out["boundary_matrix"]
    assert boundary["truth_claimed"] is False
    assert boundary["authority_granted"] is False
    assert boundary["tools_authorized"] is False
    assert boundary["belief_promoted_automatically"] is False


def test_leb_consolidation_preserves_phase19_and_phase24():
    out = build_consolidation()
    boundary = out["boundary_matrix"]
    assert boundary["phase19_yellow_preserved"] is True
    assert boundary["phase24_infrastructure_only_preserved"] is True


def test_leb_consolidation_documents_ais_integration_points():
    out = build_consolidation()
    assert "quarantine" in out["chain_summary"]["ais_precedes_real_evidence_bridge"]
    assert out["chain_summary"]["live_browsing_still_forbidden"] is True


def test_leb_consolidation_gate_green():
    code, summary = run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_LEB_LOCAL_EVIDENCE_BRIDGE_CONSOLIDATION"
