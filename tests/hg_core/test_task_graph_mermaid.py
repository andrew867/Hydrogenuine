"""
Tests for dag_to_mermaid: output shape (flowchart TD, node edges).
"""

import pytest

from hg_core.task_graph import dag_to_mermaid, DAG


def test_dag_to_mermaid_returns_string_with_flowchart_td():
    dag_dict = {
        "graph_id": "mermaid_v1",
        "version": "1.0",
        "run_policy": {},
        "inputs": {},
        "nodes": [
            {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
            {"id": "b", "type": "tool", "assigned_entity": "x", "depends_on": ["a"], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    out = dag_to_mermaid(dag_dict)
    assert isinstance(out, str)
    assert "flowchart TD" in out
    assert "a --> b" in out or "  a --> b" in out
    assert "```mermaid" in out


def test_dag_to_mermaid_accepts_dag_instance():
    dag = DAG.from_dict({
        "graph_id": "m2",
        "version": "1.0",
        "run_policy": {},
        "inputs": {},
        "nodes": [
            {"id": "start", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    })
    out = dag_to_mermaid(dag)
    assert "flowchart TD" in out
    assert "start" in out
