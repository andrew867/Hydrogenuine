from __future__ import annotations

import pytest

from hg_quantum.error_correction.barbell_builder import BarbellGraphBuilder
from hg_quantum.error_correction.ldpc_verifier import build_verification_graph, verify_coverage
from hg_quantum.error_correction.syndrome_extractor import SyndromeExtractor


def test_build_verification_graph_barbell_when_flag_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_QUANTUM2_BARBELL_TOPOLOGY_ENABLED", "true")
    graph = build_verification_graph([f"c{i}" for i in range(8)])
    report = BarbellGraphBuilder().coverage_report(graph)
    assert report.node_count == 8
    assert report.two_hop_external_coverage is True


def test_build_verification_graph_sparse_random_topology(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_TOPOLOGY", "random")
    graph = build_verification_graph([f"c{i}" for i in range(8)])
    cov = verify_coverage(graph)
    assert cov["sparse"] is True
    assert cov["node_count"] == 8


def test_extract_syndromes_detects_mismatch():
    extractor = SyndromeExtractor()
    outputs = [
        {"entity_id": "a", "summary": "result alpha"},
        {"entity_id": "b", "summary": "result beta divergent"},
    ]
    graph = extractor.build_verification_graph(outputs)
    syndromes = extractor.extract_syndromes(outputs, graph, swarm_run_id="run1")
    assert len(syndromes) >= 1


def test_decode_correction_minimum_weight():
    extractor = SyndromeExtractor()
    outputs = [
        {"entity_id": "a", "summary": "x"},
        {"entity_id": "b", "summary": "y"},
        {"entity_id": "c", "summary": "z"},
    ]
    graph = extractor.build_verification_graph(outputs)
    syndromes = extractor.extract_syndromes(outputs, graph)
    actions = extractor.decode_correction(syndromes)
    if syndromes:
        assert actions[0].target_entity in {"a", "b", "c"}
