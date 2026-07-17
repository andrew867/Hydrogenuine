"""
OS Phase 1: WorkItem queue, 2PC, policy engine, scheduler/backpressure, rebuild harness.
See .cursor/plans/operatingsystem/chapter1/operatingsystem_phase1/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.work_items import (
    create_work_item,
    update_work_item,
    assign_work_item,
    block_work_item,
    unblock_work_item,
    close_work_item,
    link_work_item,
)
from hg_core.side_effects import (
    propose_action,
    grant_approval,
    deny_approval,
    execute_action,
    verify_action,
    commit_action,
)
from hg_core.policy_engine import PolicyEngine
from hg_core.os_layer import get_prioritized_work_items, check_backpressure, apply_backpressure_if_needed
from hg_core.rebuild import rebuild_with_manifest, get_hash_manifest, generate_golden_run, check_manifest_drift
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers import run_all
from hg_core.materializers.work_items_indexer import run as run_work_items_indexer


SCOPE = {"type": "run", "id": "test_os1"}
ACTOR = {"agent_id": "agent_os1", "pubkey": "0" * 64, "key_id": "k"}


def test_work_item_create_and_update_materializes(tmp_path: Path):
    """WorkItem create/update materializes correctly."""
    wi_id = create_work_item(
        wi_type="task",
        title="Test task",
        scope=SCOPE,
        actor=ACTOR,
        description="Desc",
        priority="high",
        workspace_root=tmp_path,
    )
    assert wi_id
    update_work_item(
        work_item_id=wi_id,
        scope=SCOPE,
        actor=ACTOR,
        changes={"description": "Updated"},
        note="Note",
        workspace_root=tmp_path,
    )
    run_work_items_indexer(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "work_items.jsonl").exists()
    lines = (root / "work_items.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    obj = json.loads(lines[0])
    assert obj.get("work_item_id") == wi_id
    assert obj.get("title") == "Test task"
    assert obj.get("priority") == "high"


def test_work_item_assign_block_unblock_close_link(tmp_path: Path):
    """Assign, block, unblock, close, link emit and are indexed."""
    wi_id = create_work_item(wi_type="incident", title="Inc", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assign_work_item(work_item_id=wi_id, scope=SCOPE, actor=ACTOR, owner_agent_id="B", workspace_root=tmp_path)
    block_work_item(work_item_id=wi_id, scope=SCOPE, actor=ACTOR, reason="wait", workspace_root=tmp_path)
    unblock_work_item(work_item_id=wi_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    link_work_item(work_item_id=wi_id, scope=SCOPE, actor=ACTOR, link_type="decision", target_ref={"type": "decision", "id": "d1"}, workspace_root=tmp_path)
    close_work_item(work_item_id=wi_id, scope=SCOPE, actor=ACTOR, status="done", workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "WORK_ITEM_ASSIGNED" for _, _, ev in evs)
    assert any(ev.get("action") == "WORK_ITEM_BLOCKED" for _, _, ev in evs)
    assert any(ev.get("action") == "WORK_ITEM_CLOSED" for _, _, ev in evs)
    assert any(ev.get("action") == "WORK_ITEM_LINKED" for _, _, ev in evs)


def test_work_item_invalid_type_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="wi_type"):
        create_work_item(wi_type="invalid", title="T", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)


def test_2pc_propose_grant_execute_receipt_verify_commit(tmp_path: Path):
    """2PC: propose -> grant -> execute (receipt required) -> verify -> commit."""
    wi_id = create_work_item(wi_type="task", title="2PC task", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    action_id = propose_action(
        work_item_id=wi_id,
        tool_name="tool_x",
        idempotency_key="idem_1",
        intended_effects=["effect1"],
        risk_flags=[],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert action_id
    grant_approval(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    execute_action(action_id=action_id, scope=SCOPE, actor=ACTOR, outcome={"success": True}, workspace_root=tmp_path)
    verify_action(action_id=action_id, scope=SCOPE, actor=ACTOR, verified=True, verifier_note="ok", workspace_root=tmp_path)
    commit_action(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert (tmp_path / "artifacts" / "side_effects" / "proposals" / f"{action_id}.json").exists()
    assert (tmp_path / "artifacts" / "side_effects" / "receipts" / f"{action_id}.json").exists()
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "ACTION_PROPOSED" for _, _, ev in evs)
    assert any(ev.get("action") == "ACTION_APPROVAL_GRANTED" for _, _, ev in evs)
    assert any(ev.get("action") == "ACTION_EXECUTED" for _, _, ev in evs)
    assert any(ev.get("action") == "ACTION_VERIFIED" for _, _, ev in evs)
    assert any(ev.get("action") == "ACTION_COMMITTED" for _, _, ev in evs)


def test_2pc_deny_approval(tmp_path: Path):
    """2PC: deny approval emits ACTION_APPROVAL_DENIED."""
    wi_id = create_work_item(wi_type="task", title="Deny task", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    action_id = propose_action(work_item_id=wi_id, tool_name="t", idempotency_key="k", intended_effects=[], risk_flags=[], scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    deny_approval(action_id=action_id, scope=SCOPE, actor=ACTOR, reason="risky", workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "ACTION_APPROVAL_DENIED" for _, _, ev in evs)


def test_policy_engine_evaluate_deterministic(tmp_path: Path):
    """Policy engine evaluates fixtures deterministically."""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("""
trust_bands:
  - name: band_0
    max_action: READ
  - name: band_1
    max_action: WRITE
action_costs:
  READ: 0.1
  WRITE: 1.0
budget:
  default_limit: 100.0
  hard: true
require_approval_for_actions: [DECISION_COMMITTED]
""")
    engine = PolicyEngine.load(str(policy_path))
    r = engine.evaluate({"action": "READ", "trust_band": 0, "agency_budget": 50.0})
    assert r["allow"] is True
    assert "rationale" in r
    r2 = engine.evaluate({"action": "WRITE", "trust_band": 0, "agency_budget": 50.0})
    assert r2["allow"] is False
    scenarios = [{"action": "READ", "trust_band": 1, "agency_budget": 10.0}]
    results = engine.simulate(scenarios)
    assert len(results) == 1
    assert results[0]["allow"] is True


def test_rebuild_harness_produces_stable_manifest(tmp_path: Path):
    """Rebuild harness produces stable hash manifest on golden ledger."""
    generate_golden_run(tmp_path)
    run_all(tmp_path, rebuild=True)
    manifest1 = get_hash_manifest(tmp_path)
    assert isinstance(manifest1, dict)
    assert len(manifest1) >= 1
    run_all(tmp_path, rebuild=True)
    manifest2 = get_hash_manifest(tmp_path)
    assert manifest1 == manifest2


def test_rebuild_with_manifest(tmp_path: Path):
    """rebuild_with_manifest returns ok and manifest."""
    res = rebuild_with_manifest(tmp_path, rebuild=True)
    assert res["ok"] is True
    assert "manifest" in res


def test_check_manifest_drift(tmp_path: Path):
    """CI manifest drift: no drift when expected matches current."""
    generate_golden_run(tmp_path)
    res = rebuild_with_manifest(tmp_path, rebuild=True)
    manifest = res["manifest"]
    drift = check_manifest_drift(tmp_path, expected_manifest=manifest)
    assert drift["ok"] is True
    assert drift["drift"] == []


def test_scheduler_prioritized_work_items(tmp_path: Path):
    """get_prioritized_work_items returns incident first, then by priority."""
    create_work_item(wi_type="task", title="T1", scope=SCOPE, actor=ACTOR, priority="low", workspace_root=tmp_path)
    create_work_item(wi_type="incident", title="I1", scope=SCOPE, actor=ACTOR, priority="normal", workspace_root=tmp_path)
    run_work_items_indexer(tmp_path, rebuild=True)
    items = get_prioritized_work_items(tmp_path, status_filter=["proposed", "active"])
    assert len(items) >= 2
    types = [i.get("type") for i in items]
    assert types[0] == "incident"


def test_check_backpressure(tmp_path: Path):
    """check_backpressure returns status dict."""
    s = check_backpressure(tmp_path)
    assert "ok" in s
    assert "materializers" in s
