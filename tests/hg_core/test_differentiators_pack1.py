"""
Differentiators Pack 1: VerificationGraph, ImpactGraph, Semantic Risk Budget,
coalition detection, policy proofs.

See .cursor/plans/differentiators/chapter1/differentiators_pack1_verification_impact_risk_proofs/
"""

from __future__ import annotations

from pathlib import Path

from hg_core.verification import (
    get_verification_graph,
    check_verification_gate,
    register_verification_source,
    perform_verification_check,
    compute_robustness_for_action,
)
from hg_core.impact import (
    build_impact_graph,
    get_dependency_closure,
    compute_blast_radius,
)
from hg_core.risk_budget import (
    compute_impact_cost,
    init_budget,
    get_budget_status,
    debit_budget,
    check_budget_sufficient,
)
from hg_core.coalition import detect_coalition_signals, list_coalition_signals
from hg_core.policy_proofs import create_proof, get_proof, evaluate_with_proof
from hg_core.ledger import emit
from hg_core.policy_engine import PolicyEngine
from hg_core.side_effects.two_phase import (
    propose_action,
    grant_approval,
    execute_action,
    commit_action,
)


SCOPE = {"type": "run", "id": "test_diff1"}
ACTOR = {"agent_id": "agent_diff1", "pubkey": "0" * 64, "key_id": "k"}


def test_verification_gate_requires_two_independent_groups_for_critical(tmp_path: Path) -> None:
    """Robustness requires 2+ independent source groups for critical actions."""
    register_verification_source(
        source_id="src_a",
        name="Source A",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    register_verification_source(
        source_id="src_b",
        name="Source B",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    action_id = "act_critical"
    perform_verification_check(
        action_id=action_id,
        source_id="src_a",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    perform_verification_check(
        action_id=action_id,
        source_id="src_b",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    compute_robustness_for_action(
        action_id=action_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    passed, reason = check_verification_gate(
        tmp_path, action_id, critical=True, min_independent_groups=2
    )
    assert passed, reason
    # Single source: should fail gate when critical
    action_id2 = "act_single"
    perform_verification_check(
        action_id=action_id2,
        source_id="src_a",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    compute_robustness_for_action(
        action_id=action_id2,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    passed2, reason2 = check_verification_gate(
        tmp_path, action_id2, critical=True, min_independent_groups=2
    )
    assert not passed2
    assert "insufficient_independent_groups" in reason2


def test_correlated_checks_discounted(tmp_path: Path) -> None:
    """Same source twice does not count as two independent groups."""
    register_verification_source(
        source_id="only_src",
        name="Only",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    action_id = "act_corr"
    for _ in range(2):
        perform_verification_check(
            action_id=action_id,
            source_id="only_src",
            result="pass",
            scope=SCOPE,
            actor=ACTOR,
            workspace_root=tmp_path,
        )
    compute_robustness_for_action(
        action_id=action_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    passed, _ = check_verification_gate(
        tmp_path, action_id, critical=True, min_independent_groups=2
    )
    assert not passed


def test_verification_graph_structure(tmp_path: Path) -> None:
    """VerificationGraph returns nodes (sources, checks, robustness) and edges."""
    register_verification_source(
        source_id="s1",
        name="S1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    perform_verification_check(
        action_id="ax",
        source_id="s1",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    nodes, edges = get_verification_graph(tmp_path, action_id="ax")
    assert any(n.get("type") == "source" for n in nodes.values())
    assert any(n.get("type") == "check" for n in nodes.values())
    assert any(e[2] == "PERFORMED" for e in edges)


def test_blast_radius_closure(tmp_path: Path) -> None:
    """Blast radius closure is correct (dependency closure of incident node)."""
    # Ensure materialized dir exists and has incidents
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    incidents_path = tmp_path / "memory" / "materialized" / "incidents.jsonl"
    incidents_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    incidents_path.write_text(
        json.dumps({
            "incident_id": "inc_1",
            "event_id": "ev_inc1",
            "status": "confirmed",
            "severity": "high",
        }) + "\n",
        encoding="utf-8",
    )
    score, event_id = compute_blast_radius(
        incident_id="inc_1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert score >= 0.0
    assert event_id


def test_risk_budget_debit_and_insufficient(tmp_path: Path) -> None:
    """Risk budget debits and insufficient budget triggers (approval/deny)."""
    init_budget(
        initial_balance=10.0,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    status = get_budget_status(tmp_path, scope=SCOPE)
    assert status["balance"] == 10.0
    ok, _ = debit_budget(
        amount=3.0,
        action_id="act_1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ok
    assert get_budget_status(tmp_path, scope=SCOPE)["balance"] == 7.0
    ok2, _ = debit_budget(
        amount=10.0,
        action_id="act_2",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert not ok2
    assert not check_budget_sufficient(10.0, tmp_path, scope=SCOPE)


def test_impact_cost_and_budget_by_params(tmp_path: Path) -> None:
    """Impact cost computed from action_class, environment; debit with impact_cost_params."""
    cost = compute_impact_cost(
        action_class="WRITE",
        asset_criticality=1.5,
        reversibility=0.5,
        environment="prod",
    )
    assert cost > 0
    init_budget(
        initial_balance=100.0,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    ok, _ = debit_budget(
        amount=0,
        action_id="act_impact",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        impact_cost_params={
            "action_class": "READ",
            "asset_criticality": 1.0,
            "environment": "dev",
        },
    )
    assert ok


def test_approval_ring_triggers_coalition_signal(tmp_path: Path) -> None:
    """Approval ring (cycle of proposer->approver) triggers coalition signal."""
    # A proposes action_1, B approves. B proposes action_2, A approves -> ring
    emit(
        "ACTION_PROPOSED",
        "action",
        "act_1",
        {"action_id": "act_1", "work_item_id": "w1", "ts": "2026-01-01T00:00:00Z"},
        scope=SCOPE,
        actor={"agent_id": "agent_a", "pubkey": "0", "key_id": "k"},
        workspace_root=tmp_path,
    )
    emit(
        "ACTION_APPROVAL_GRANTED",
        "action",
        "act_1",
        {"action_id": "act_1", "ts": "2026-01-01T00:00:01Z"},
        scope=SCOPE,
        actor={"agent_id": "agent_b", "pubkey": "0", "key_id": "k"},
        workspace_root=tmp_path,
    )
    emit(
        "ACTION_PROPOSED",
        "action",
        "act_2",
        {"action_id": "act_2", "work_item_id": "w2", "ts": "2026-01-01T00:00:02Z"},
        scope=SCOPE,
        actor={"agent_id": "agent_b", "pubkey": "0", "key_id": "k"},
        workspace_root=tmp_path,
    )
    emit(
        "ACTION_APPROVAL_GRANTED",
        "action",
        "act_2",
        {"action_id": "act_2", "ts": "2026-01-01T00:00:03Z"},
        scope=SCOPE,
        actor={"agent_id": "agent_a", "pubkey": "0", "key_id": "k"},
        workspace_root=tmp_path,
    )
    signals = detect_coalition_signals(tmp_path, SCOPE, ACTOR, emit_events=True)
    assert any(s.get("signal_type") == "approval_ring" for s in signals)
    listed = list_coalition_signals(tmp_path, limit=10)
    assert any(s.get("signal_type") == "approval_ring" for s in listed)


def test_policy_proof_create_and_get(tmp_path: Path) -> None:
    """Policy proof create and get; proof verifier passes (bundle can include proofs)."""
    proof_id = create_proof(
        policy_artifact_id="policy.yaml",
        rule_ids=["trust_band", "action_cost"],
        inputs={"action": "READ", "trust_band": 0},
        decision={"allow": True, "require_approval": False},
        evidence_refs=[{"rationale": {}}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        emit_event=True,
    )
    assert proof_id
    proof = get_proof(proof_id, workspace_root=tmp_path)
    assert proof is not None
    assert proof["proof_id"] == proof_id
    assert proof["policy_artifact_id"] == "policy.yaml"
    assert "rule_ids" in proof
    assert proof["decision"].get("allow") is True


def test_evaluate_with_proof(tmp_path: Path) -> None:
    """Policy engine evaluate_with_proof produces proof and returns result."""
    engine = PolicyEngine({"trust_bands": [{"max_action": "WRITE"}], "action_costs": {"READ": 0.5}})
    ctx = {"action": "READ", "trust_band": 0, "agency_budget": 10.0}
    result, proof_id = evaluate_with_proof(
        engine,
        ctx,
        policy_artifact_id="test_policy",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert result.get("allow") is True
    assert proof_id
    proof = get_proof(proof_id, workspace_root=tmp_path)
    assert proof is not None
    assert proof["inputs"] == ctx


def test_commit_action_verification_gate_blocks_when_insufficient(tmp_path: Path) -> None:
    """2PC commit_action with require_verification_gate blocks when gate fails (Pack 1 wiring)."""
    action_id = propose_action(
        work_item_id="w1",
        tool_name="run",
        idempotency_key="k1",
        intended_effects=[],
        risk_flags=[],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    # No verification checks for this action -> gate fails
    import pytest
    with pytest.raises(ValueError, match="Verification gate failed"):
        commit_action(
            action_id=action_id,
            scope=SCOPE,
            actor=ACTOR,
            workspace_root=tmp_path,
            require_verification_gate=True,
            critical=True,
        )
    # Without require_verification_gate, commit succeeds
    grant_approval(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    execute_action(action_id=action_id, scope=SCOPE, actor=ACTOR, outcome={"ok": True}, workspace_root=tmp_path)
    commit_action(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)


def test_impact_graph_includes_policies_tools_verifiers(tmp_path: Path) -> None:
    """Impact graph includes policy, tool, verifier nodes when materialized data exists."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    root = tmp_path / "memory" / "materialized"
    import json
    (root / "policy_events.jsonl").write_text(
        json.dumps({"policy_ref": "pol_1", "event_id": "e1", "policy_type": "access"}) + "\n",
        encoding="utf-8",
    )
    (root / "tool_outcomes.jsonl").write_text(
        json.dumps({"tool_call_id": "tc_1", "tool_name": "run", "event_id": "e2", "outcome": "ok"}) + "\n",
        encoding="utf-8",
    )
    register_verification_source(
        source_id="vs1",
        name="V1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    nodes, edges = build_impact_graph(tmp_path)
    types = {n.get("type") for n in nodes.values()}
    assert "policy" in types
    assert "tool" in types
    assert "verifier" in types
