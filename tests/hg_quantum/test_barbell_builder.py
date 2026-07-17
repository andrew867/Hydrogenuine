from __future__ import annotations

import os

import pytest

from hg_quantum.error_correction.barbell_builder import BarbellGraphBuilder
from hg_quantum.error_correction.ldpc_verifier import build_verification_graph
from hg_realtime.swarm.contracts import SwarmPlan


def _clustered_plan() -> SwarmPlan:
    tasks = []
    for g in ("alpha", "beta", "gamma"):
        for i in range(3):
            tasks.append({"entity_id": f"{g}_{i}", "subtask_group": g, "role": "worker"})
    return SwarmPlan(summary="clustered", tasks=tasks)


def test_build_clusters_match_subtask_groups():
    graph = BarbellGraphBuilder().build(_clustered_plan())
    clusters = {"alpha": [f"alpha_{i}" for i in range(3)], "beta": [f"beta_{i}" for i in range(3)]}
    for members in clusters.values():
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                assert (a, b) in graph.edge_pairs or (b, a) in graph.edge_pairs


def test_build_one_crosslink_per_cluster_pair():
    builder = BarbellGraphBuilder()
    graph = builder.build(_clustered_plan())
    report = builder.coverage_report(graph)
    assert report.cross_link_count == 3  # C(3,2)


def test_two_hop_external_coverage():
    graph = BarbellGraphBuilder().build(_clustered_plan())
    report = BarbellGraphBuilder().coverage_report(graph)
    assert report.two_hop_external_coverage is True


def test_coverage_report_counts_checks():
    graph = BarbellGraphBuilder().build(_clustered_plan())
    report = BarbellGraphBuilder().coverage_report(graph)
    assert report.edge_count == len(graph.edge_pairs)
    assert report.node_count == 9


def test_default_topology_is_barbell(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HG_QUANTUM_LDPC_TOPOLOGY", raising=False)
    from hg_quantum.config import get_ldpc_topology

    assert get_ldpc_topology() == "barbell"


def test_random_topology_available_behind_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_TOPOLOGY", "random")
    from hg_quantum.config import get_ldpc_topology

    assert get_ldpc_topology() == "random"
    nodes = [f"n{i}" for i in range(6)]
    graph = build_verification_graph(nodes)
    assert len(graph.edge_pairs) > 0
    barbell = BarbellGraphBuilder().build_from_nodes(nodes, cluster_map={n: "solo" for n in nodes})
    assert len(graph.edge_pairs) <= len(barbell.edge_pairs)
