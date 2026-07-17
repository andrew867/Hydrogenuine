"""
OS Phase 4: Autonomy loops, value model, governance contracts, learning suggestions, dashboards.
See .cursor/plans/operatingsystem/chapter4/operatingsystem_phase4/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.autonomy import (
    start_loop,
    stop_loop,
    tick_loop,
    select_work_item,
    publish_plan,
    record_plan_step_executed,
    record_loop_blocked,
    publish_loop_summary,
    run_loop_once,
)
from hg_core.values import record_value_judgment, build_value_dataset_artifact, load_value_dataset, VALUE_DIMENSIONS
from hg_core.governance import (
    publish_governance_contract,
    record_approval_policy_applied,
    create_delegation_contract,
    record_escalation_route_taken,
    load_contract,
)
from hg_core.learning import (
    publish_tuning_suggestion,
    record_policy_rollout_started,
    record_policy_rollout_completed,
    record_policy_rollout_rolled_back,
)
from hg_core.dashboards import get_dashboard_for_role, get_narrative_report
from hg_core.work_items import create_work_item
from hg_core.materializers import run_all


SCOPE = {"type": "run", "id": "test_os4"}
ACTOR = {"agent_id": "agent_os4", "pubkey": "0" * 64, "key_id": "k"}


def test_autonomy_loop_events(tmp_path: Path):
    """LOOP_STARTED, LOOP_TICK, WORK_ITEM_SELECTED, PLAN_GENERATED, LOOP_BLOCKED, LOOP_SUMMARY_PUBLISHED, LOOP_STOPPED."""
    lid = start_loop(scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert lid.startswith("loop_")
    tick_loop(loop_id=lid, scope=SCOPE, actor=ACTOR, stats={"count": 1}, workspace_root=tmp_path)
    wi_id = create_work_item(scope=SCOPE, actor=ACTOR, wi_type="task", title="WI", workspace_root=tmp_path)
    select_work_item(loop_id=lid, work_item_id=wi_id, scope=SCOPE, actor=ACTOR, reason="next", workspace_root=tmp_path)
    plan_path = tmp_path / "artifacts" / "plans" / "p1.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}")
    publish_plan(loop_id=lid, work_item_id=wi_id, plan_artifact_path=str(plan_path), scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_plan_step_executed(loop_id=lid, work_item_id=wi_id, step_index=0, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_loop_blocked(loop_id=lid, scope=SCOPE, actor=ACTOR, reason="approval", waiting_on="human", workspace_root=tmp_path)
    summary_path = tmp_path / "artifacts" / "loops" / "sum.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("{}")
    publish_loop_summary(loop_id=lid, scope=SCOPE, actor=ACTOR, summary_artifact_path=str(summary_path), workspace_root=tmp_path)
    stop_loop(loop_id=lid, scope=SCOPE, actor=ACTOR, reason="done", workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "LOOP_STARTED" in actions
    assert "LOOP_TICK" in actions
    assert "WORK_ITEM_SELECTED" in actions
    assert "PLAN_GENERATED" in actions
    assert "LOOP_BLOCKED" in actions
    assert "LOOP_SUMMARY_PUBLISHED" in actions
    assert "LOOP_STOPPED" in actions


def test_run_loop_once(tmp_path: Path):
    """run_loop_once selects work item when queue has items; respects backpressure."""
    run_all(tmp_path, rebuild=True)
    result = run_loop_once(workspace_root=tmp_path, scope=SCOPE, actor=ACTOR, stop_on_backpressure=False)
    assert "loop_id" in result or result.get("blocked")
    create_work_item(scope=SCOPE, actor=ACTOR, wi_type="task", title="Q", workspace_root=tmp_path)
    run_all(tmp_path, rebuild=True)
    result2 = run_loop_once(workspace_root=tmp_path, scope=SCOPE, actor=ACTOR, stop_on_backpressure=False)
    assert result2.get("selected_work_item_id") or result2.get("blocked") is not None


def test_value_judgment_and_dataset(tmp_path: Path):
    """record_value_judgment emits VALUE_JUDGMENT_RECORDED; build_value_dataset_artifact writes artifact."""
    jid = record_value_judgment(
        domain="ops",
        scenario_artifact_id="scen_1",
        prefer_a_over_b=True,
        action_a="A",
        action_b="B",
        dimensions=[{"dimension": "harm_reduction", "weight": 0.8}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert jid.startswith("vj_")
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "VALUE_JUDGMENT_RECORDED" in actions
    path = build_value_dataset_artifact(tmp_path, version="1.0")
    assert Path(path).exists()
    data = load_value_dataset(tmp_path, "1.0")
    assert "judgments" in data and "dimensions" in data
    assert VALUE_DIMENSIONS


def test_governance_contracts(tmp_path: Path):
    """publish_governance_contract, record_approval_policy_applied, create_delegation_contract, record_escalation_route_taken."""
    cid = publish_governance_contract(
        contract={"approvers": ["admin"], "delegation_bounds": {}, "response_hours": 24},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert cid.startswith("gc_")
    assert load_contract(tmp_path, cid) is not None
    record_approval_policy_applied(contract_id=cid, decision_id="d1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    create_delegation_contract(from_agent_id="a1", to_agent_id="a2", constraints={"max_work_items": 5}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_escalation_route_taken(paged_agent_ids=["oncall"], reason="incident", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "GOVERNANCE_CONTRACT_PUBLISHED" in actions
    assert "APPROVAL_POLICY_APPLIED" in actions
    assert "DELEGATION_CONTRACT_CREATED" in actions
    assert "ESCALATION_ROUTE_TAKEN" in actions


def test_learning_suggestions_and_rollout(tmp_path: Path):
    """publish_tuning_suggestion (artifact only); POLICY_ROLLOUT_* events."""
    sid = publish_tuning_suggestion(
        kind="policy",
        suggestion_payload={"suggested_weights": {}},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert sid.startswith("tune_")
    with pytest.raises(ValueError, match="kind"):
        publish_tuning_suggestion(kind="invalid", suggestion_payload={}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_policy_rollout_started(rollout_id="r1", policy_ref="policy_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_policy_rollout_completed(rollout_id="r1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_policy_rollout_rolled_back(rollout_id="r2", scope=SCOPE, actor=ACTOR, reason="rollback", workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "TUNING_SUGGESTION_PUBLISHED" in actions
    assert "POLICY_ROLLOUT_STARTED" in actions
    assert "POLICY_ROLLOUT_COMPLETED" in actions
    assert "POLICY_ROLLOUT_ROLLED_BACK" in actions


def test_dashboards_and_reports(tmp_path: Path):
    """get_dashboard_for_role and get_narrative_report return evidence-backed structures."""
    run_all(tmp_path, rebuild=True)
    d = get_dashboard_for_role(tmp_path, "operator")
    assert d["role"] == "operator"
    assert "widgets" in d
    di = get_dashboard_for_role(tmp_path, "investor", investor_mode=True)
    assert di["investor_mode"] is True
    r = get_narrative_report(tmp_path, "decision_report")
    assert r["report_type"] == "decision_report"
    assert "evidence_refs" in r
    r2 = get_narrative_report(tmp_path, "incident_report", investor_mode=True)
    assert r2.get("redact_sensitive") is True
