"""SQP-3 provenance graph builder tests."""

from __future__ import annotations

import pytest

from hg_runtime.source_quality_provenance.gate import validate_sqp3_gate
from hg_runtime.source_quality_provenance.provenance_edge_builder import build_provenance_edge
from hg_runtime.source_quality_provenance.provenance_graph_builder import (
    build_provenance_graph_layer,
    build_sqp3_provenance_inputs,
    lineage_completeness,
)
from hg_runtime.source_quality_provenance.provenance_node_builder import build_provenance_node
from hg_runtime.source_quality_provenance.provenance_replay import replay_provenance_graph
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVENANCE_EDGE_TYPES,
    PROVENANCE_NODE_TYPES,
    SQPBoundaryError,
)


def _layer():
    return build_provenance_graph_layer(build_sqp3_provenance_inputs())


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_3_PROVENANCE_GRAPH",
        "reviewed_beta_green": True,
        "sqp0_green": True,
        "sqp1_green": True,
        "sqp2_green": True,
        "source_manifests_consumed": True,
        "evidence_receipts_consumed": True,
        "claim_links_consumed": True,
        "reviewed_links_consumed": True,
        "promotion_requests_consumed": True,
        "belief_revisions_consumed": True,
        "fingerprints_consumed": True,
        "quality_scores_consumed": True,
        "provenance_nodes_written": True,
        "provenance_edges_written": True,
        "provenance_graph_written": True,
        "all_node_types_present": True,
        "all_edge_types_present": True,
        "lineage_complete": True,
        "provenance_not_authority": True,
        "graph_path_not_proof": True,
        "lineage_not_truth": True,
        "duplicate_not_corroboration": True,
        "many_copies_not_many_sources": True,
        "graph_cannot_authorize_action": True,
        "graph_cannot_authorize_tools": True,
        "graph_cannot_promote_belief": True,
        "old_records_preserved": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_node_hashes": True,
        "replay_preserves_edge_hashes": True,
        "replay_preserves_graph_hash": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Node / edge builders --------------------------------------------------

def test_sqp3_node_builder_rejects_unknown_type():
    with pytest.raises(SQPBoundaryError):
        build_provenance_node(node_id="n", node_type="NOT_A_TYPE", ref="r")


def test_sqp3_edge_builder_rejects_unknown_type():
    with pytest.raises(SQPBoundaryError):
        build_provenance_edge(edge_id="e", from_node_id="a", to_node_id="b", edge_type="NOT_AN_EDGE", evidence_ref="r")


def test_sqp3_node_is_non_authoritative():
    n = build_provenance_node(node_id="n", node_type="SOURCE", ref="r", source_id="s")
    assert n["provenance_treated_as_authority"] is False
    assert n["lineage_treated_as_truth"] is False
    assert n["node_is_proof"] is False
    assert n["node_promotes_belief"] is False


def test_sqp3_edge_is_not_corroboration():
    e = build_provenance_edge(edge_id="e", from_node_id="a", to_node_id="b", edge_type="DUPLICATE_OF", evidence_ref="r")
    assert e["duplicate_treated_as_corroboration"] is False
    assert e["edge_is_proof"] is False


# --- Graph composition -----------------------------------------------------

def test_sqp3_graph_has_all_node_types():
    present = {n["node_type"] for n in _layer()["nodes"]}
    assert PROVENANCE_NODE_TYPES <= present


def test_sqp3_graph_has_all_edge_types():
    present = {e["edge_type"] for e in _layer()["edges"]}
    assert PROVENANCE_EDGE_TYPES <= present


def test_sqp3_lineage_complete():
    m = _layer()["manifest"]
    assert m["lineage_complete"] is True
    assert m["dangling_edges"] == []
    assert m["orphan_nodes"] == []
    assert m["missing_node_types"] == []
    assert m["missing_edge_types"] == []


def test_sqp3_duplicate_collapses_logical_sources():
    m = _layer()["manifest"]
    # Three SOURCE nodes, but one is a duplicate copy -> fewer distinct logicals.
    assert m["source_node_count"] == 3
    assert m["distinct_logical_source_count"] < m["source_node_count"]


def test_sqp3_has_duplicate_of_edge():
    edges = _layer()["edges"]
    assert any(e["edge_type"] == "DUPLICATE_OF" for e in edges)


def test_sqp3_graph_is_not_proof_or_authority():
    g = _layer()["graph"]
    assert g["graph_is_proof"] is False
    assert g["graph_path_is_proof"] is False
    assert g["provenance_treated_as_authority"] is False
    assert g["graph_authorizes_action"] is False
    assert g["graph_promotes_belief"] is False
    assert g["many_copies_treated_as_many_sources"] is False


# --- Missing lineage blocks GREEN ------------------------------------------

def test_sqp3_missing_lineage_detected():
    layer = _layer()
    nodes = layer["nodes"]
    # Drop all EVIDENCE_RECEIPT nodes -> dangling edges + missing node type.
    pruned = [n for n in nodes if n["node_type"] != "EVIDENCE_RECEIPT"]
    lineage = lineage_completeness(pruned, layer["edges"])
    assert lineage["lineage_complete"] is False
    assert "EVIDENCE_RECEIPT" in lineage["missing_node_types"]
    assert lineage["dangling_edges"]


# --- Replay ----------------------------------------------------------------

def test_sqp3_replay_preserves_hashes():
    layer = _layer()
    inputs = build_sqp3_provenance_inputs()
    replay = replay_provenance_graph(
        inputs,
        [n["record_hash"] for n in layer["nodes"]],
        [e["record_hash"] for e in layer["edges"]],
        layer["graph"]["graph_hash"],
        layer["manifest"]["manifest_hash"],
    )
    assert replay["replay_preserves_node_hashes"] is True
    assert replay["replay_preserves_edge_hashes"] is True
    assert replay["replay_preserves_graph_hash"] is True
    assert replay["replay_preserves_manifest_hash"] is True


def test_sqp3_replay_rejects_mutation():
    inputs = build_sqp3_provenance_inputs()
    replay = replay_provenance_graph(inputs, ["mutated"], ["mutated"], "mutated", "mutated")
    assert replay["replay_preserves_node_hashes"] is False
    assert replay["replay_preserves_graph_hash"] is False


def test_sqp3_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_sqp3_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_sqp3_gate_passes_full_summary():
    assert validate_sqp3_gate(_summary())["ok"] is True


def test_sqp3_gate_refuses_incomplete_lineage():
    assert validate_sqp3_gate(_summary(lineage_complete=False))["ok"] is False


def test_sqp3_gate_refuses_missing_node_or_edge_types():
    assert validate_sqp3_gate(_summary(all_node_types_present=False))["ok"] is False
    assert validate_sqp3_gate(_summary(all_edge_types_present=False))["ok"] is False


def test_sqp3_gate_refuses_provenance_as_authority():
    assert validate_sqp3_gate(_summary(provenance_treated_as_authority=True))["ok"] is False


def test_sqp3_gate_refuses_graph_as_proof():
    assert validate_sqp3_gate(_summary(graph_path_is_proof=True))["ok"] is False


def test_sqp3_gate_refuses_lineage_as_truth():
    assert validate_sqp3_gate(_summary(lineage_treated_as_truth=True))["ok"] is False


def test_sqp3_gate_refuses_duplicate_as_corroboration():
    assert validate_sqp3_gate(_summary(duplicate_treated_as_corroboration=True))["ok"] is False


def test_sqp3_gate_refuses_graph_authorizing_action_or_belief():
    assert validate_sqp3_gate(_summary(graph_authorizes_action=True))["ok"] is False
    assert validate_sqp3_gate(_summary(graph_promotes_belief=True))["ok"] is False


def test_sqp3_gate_refuses_web_provider_or_live_effects():
    assert validate_sqp3_gate(_summary(web_browse_performed=True))["ok"] is False
    assert validate_sqp3_gate(_summary(external_provider_calls_made=True))["ok"] is False
    assert validate_sqp3_gate(_summary(live_external_side_effects_created=True))["ok"] is False
