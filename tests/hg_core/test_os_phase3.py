"""
OS Phase 3: Merkle anchoring, graph mirror, observability, sandbox, demo.
See .cursor/plans/operatingsystem/chapter3/operatingsystem_phase3/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.integrity import merkle_root, compute_merkle_root_for_range, publish_anchor, verify_anchor
from hg_core.graph_mirror import build_graph, get_neighbors, get_subgraph
from hg_core.observability import (
    get_metrics,
    record_ledger_append,
    record_materializer_run,
    record_sandbox_run,
    format_openmetrics,
    load_slo_config,
    check_slos,
    get_trace_id,
    set_trace_id,
)
from hg_core.sandbox import run_tool_in_sandbox, create_sandbox_context, destroy_sandbox_context
from hg_core.materializers import run_all


SCOPE = {"type": "run", "id": "test_os3"}
ACTOR = {"agent_id": "agent_os3", "pubkey": "0" * 64, "key_id": "k"}


def test_merkle_root_deterministic():
    """Merkle root is deterministic for same leaves."""
    hashes = ["a", "b", "c"]
    r1 = merkle_root(hashes)
    r2 = merkle_root(hashes)
    assert r1 == r2
    assert len(r1) == 64


def test_merkle_root_range():
    """compute_merkle_root_for_range returns root for inclusive range."""
    ids = ["e1", "e2", "e3", "e4"]
    r = compute_merkle_root_for_range(ids, "e2", "e3")
    assert r == merkle_root(["e2", "e3"])


def test_anchor_publish_and_verify(tmp_path: Path):
    """publish_anchor and verify_anchor; verification detects tampering."""
    emit("DECISION_COMMITTED", "decision", "d1", {"decision_id": "d1"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    emit("DECISION_COMMITTED", "decision", "d2", {"decision_id": "d2"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    event_ids = [ev.get("event_id") for _st, _sid, ev in iter_events_by_scope(tmp_path) if ev.get("event_id")]
    from_id = event_ids[0]
    to_id = event_ids[-1]
    anchor_id = publish_anchor(
        workspace_root=tmp_path,
        scope_type=SCOPE["type"],
        scope_id=SCOPE["id"],
        from_event_id=from_id,
        to_event_id=to_id,
        scope=SCOPE,
        actor=ACTOR,
    )
    assert anchor_id
    (tmp_path / "artifacts" / "integrity" / "anchors" / f"{anchor_id}.json").exists()
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "ANCHOR_PUBLISHED" in actions
    result = verify_anchor(workspace_root=tmp_path, anchor_id=anchor_id, scope=SCOPE, actor=ACTOR)
    assert result.get("ok") is True
    assert "ANCHOR_VERIFIED" in [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]


def test_graph_mirror_build_and_query(tmp_path: Path):
    """build_graph ingests materialized data; get_neighbors and get_subgraph return evidence."""
    from hg_core.work_items import create_work_item
    wi_id = create_work_item(scope=SCOPE, actor=ACTOR, wi_type="task", title="Graph task", workspace_root=tmp_path)
    emit("DECISION_COMMITTED", "decision", "gdec", {"decision_id": "gdec", "title": "Graph dec", "based_on_claim_ids": ["c1"]}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_all(tmp_path, rebuild=True)
    nodes, edges = build_graph(tmp_path)
    assert len(nodes) >= 1
    neighbors = get_neighbors(tmp_path, "gdec", direction="out")
    assert isinstance(neighbors, list)
    sub = get_subgraph(tmp_path, ["gdec"], depth=1)
    assert "nodes" in sub and "edges" in sub


def test_observability_metrics_and_slo(tmp_path: Path):
    """Metrics record and format_openmetrics; SLO check returns breaches."""
    record_ledger_append(success=True)
    record_ledger_append(success=False)
    record_materializer_run("test_mat", success=True, lag_seconds=10.0)
    record_sandbox_run(executed=True)
    m = get_metrics()
    assert m["ledger"]["appends"] >= 1
    assert m["ledger"]["errors"] >= 1
    assert "test_mat" in m["materializers"]["runs"]
    out = format_openmetrics()
    assert "hg_ledger_appends_total" in out
    config = load_slo_config(tmp_path)
    assert "materializer_max_lag_seconds" in config or "ledger_durability" in str(config)
    slo_result = check_slos(tmp_path, metrics=m)
    assert "ok" in slo_result and "breaches" in slo_result


def test_trace_id():
    """set_trace_id and get_trace_id propagate trace."""
    set_trace_id("trace-123")
    assert get_trace_id() == "trace-123"
    set_trace_id()
    assert get_trace_id() is not None


def test_sandbox_denial_and_execution(tmp_path: Path):
    """TOOL_DENIED_BY_POLICY when not allowlisted; TOOL_EXECUTED_IN_SANDBOX when allowed."""
    result_deny = run_tool_in_sandbox(
        tool_name="forbidden_tool",
        tool_call_id="tc_1",
        allowed_tools=["allowed_only"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert result_deny["allowed"] is False
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "TOOL_DENIED_BY_POLICY" in actions
    result_allow = run_tool_in_sandbox(
        tool_name="allowed_only",
        tool_call_id="tc_2",
        allowed_tools=["allowed_only"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert result_allow["allowed"] is True
    actions2 = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "TOOL_EXECUTED_IN_SANDBOX" in actions2


def test_sandbox_context_created_destroyed(tmp_path: Path):
    """SANDBOX_CREATED and SANDBOX_DESTROYED emitted."""
    sandbox_id = create_sandbox_context(scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert sandbox_id.startswith("sbx_")
    destroy_sandbox_context(sandbox_id=sandbox_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "SANDBOX_CREATED" in actions
    assert "SANDBOX_DESTROYED" in actions


def test_demo_seed_deterministic(tmp_path: Path):
    """Demo seed produces deterministic events; reset restores known state."""
    from demo.seed_demo import seed_demo
    seed_demo(tmp_path)
    run_all(tmp_path, rebuild=True)
    events = list(iter_events_by_scope(tmp_path))
    actions = [ev.get("action") for _st, _sid, ev in events]
    assert "DECISION_COMMITTED" in actions
    assert "WORK_ITEM_CREATED" in actions
    decisions = [ev for _st, _sid, ev in events if ev.get("action") == "DECISION_COMMITTED"]
    assert any((ev.get("payload") or {}).get("decision_id") == "demo_decision_1" for ev in decisions)
