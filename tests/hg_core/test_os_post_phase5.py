"""
OS Post-Phase 5: Verification robustness, versioned materializers, impact graph, offline bundles,
governance UX batching/fatigue, policy diff risk.

See .cursor/plans/operatingsystem/chapter6/post_phase5_ultimate_framework/
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.verification import (
    register_verification_source,
    perform_verification_check,
    compute_robustness_for_action,
    record_verification_insufficient,
    get_robustness_score,
)
from hg_core.replay import (
    register_materializer_version,
    record_materializer_run,
    publish_replay_compat_profile,
    resolve_versions_for_replay,
)
from hg_core.impact import (
    build_impact_graph,
    get_dependency_closure,
    compute_blast_radius,
)
from hg_core.bundles.offline import build_offline_bundle
from hg_core.governance import (
    rank_approvals_by_risk,
    create_approval_batch,
    record_approval_batch_approved,
    record_fatigue_limit_reached,
    request_audit_spotcheck,
    record_audit_spotcheck_completed,
)
from hg_core.policy import compute_policy_diff_risk


SCOPE = {"type": "run", "id": "test_os_post5"}
ACTOR = {"agent_id": "agent_post5", "pubkey": "0" * 64, "key_id": "k"}


def test_verification_robustness_flow(tmp_path: Path):
    """VERIFICATION_SOURCE_REGISTERED, VERIFICATION_CHECK_PERFORMED, VERIFICATION_ROBUSTNESS_COMPUTED, VERIFICATION_INSUFFICIENT."""
    # Simulate an action
    action_id = "act_1"
    # Register two sources
    register_verification_source(
        source_id="src_health",
        name="Health probe",
        scope=SCOPE,
        actor=ACTOR,
        reliability_score=0.9,
        workspace_root=tmp_path,
    )
    register_verification_source(
        source_id="src_db",
        name="DB readback",
        scope=SCOPE,
        actor=ACTOR,
        reliability_score=0.95,
        workspace_root=tmp_path,
    )
    perform_verification_check(
        action_id=action_id,
        source_id="src_health",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    perform_verification_check(
        action_id=action_id,
        source_id="src_db",
        result="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    score, _ = compute_robustness_for_action(
        action_id=action_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert 0.0 < score <= 1.0
    # Insufficient verification event
    record_verification_insufficient(
        action_id="act_2",
        scope=SCOPE,
        actor=ACTOR,
        reason="no_sources",
        workspace_root=tmp_path,
    )
    # Stored score lookup
    stored = get_robustness_score(tmp_path, action_id)
    assert stored == score
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "VERIFICATION_SOURCE_REGISTERED" in actions
    assert "VERIFICATION_CHECK_PERFORMED" in actions
    assert "VERIFICATION_ROBUSTNESS_COMPUTED" in actions
    assert "VERIFICATION_INSUFFICIENT" in actions


def test_versioned_materializers_and_replay(tmp_path: Path):
    """MATERIALIZER_VERSION_REGISTERED, MATERIALIZER_RUN_RECORDED, REPLAY_COMPAT_PROFILE_PUBLISHED, resolve_versions_for_replay."""
    register_materializer_version(
        name="extras_indexer",
        version="1.0.0",
        scope=SCOPE,
        actor=ACTOR,
        code_hash="deadbeef",
        event_taxonomy_version="v1",
        policy_schema_version="p1",
        workspace_root=tmp_path,
    )
    record_materializer_run(
        materializer_name="extras_indexer",
        materializer_version="1.0.0",
        scope=SCOPE,
        actor=ACTOR,
        ledger_anchor_range={"from_event_id": "e1", "to_event_id": "e2"},
        policy_artifact_ids=["policy1"],
        workspace_root=tmp_path,
    )
    publish_replay_compat_profile(
        profile_id="default_v1",
        scope=SCOPE,
        actor=ACTOR,
        materializer_versions=[{"name": "extras_indexer", "version": "1.0.0"}],
        event_taxonomy_version="v1",
        workspace_root=tmp_path,
    )
    plan = resolve_versions_for_replay(tmp_path, tenant_id="t1", environment="prod")
    assert plan["plan_id"] != "none"
    assert plan["materializer_versions"]


def test_impact_graph_and_blast_radius(tmp_path: Path):
    """Impact graph from materialized data and BLAST_RADIUS_COMPUTED."""
    # Seed ledger-backed decision data and a materialized incident projection.
    emit(
        "DECISION_COMMITTED",
        "decision",
        "d1",
        {"decision_id": "d1", "title": "Dec1", "based_on_claim_ids": ["c1"]},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    mat_root = tmp_path / "memory" / "materialized"
    mat_root.mkdir(parents=True, exist_ok=True)
    incidents = mat_root / "incidents.jsonl"
    incidents.write_text(
        json.dumps({"incident_id": "inc1", "status": "candidate", "severity": "high", "event_id": "e_inc1"}) + "\n",
        encoding="utf-8",
    )
    nodes, edges = build_impact_graph(tmp_path)
    assert any(nid.startswith("decision:") for nid in nodes)
    closure = get_dependency_closure(tmp_path, "incident:inc1")
    assert isinstance(closure, list)
    score, _ = compute_blast_radius(incident_id="inc1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert score >= 0.0
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "BLAST_RADIUS_COMPUTED" in actions


def test_offline_bundle_and_verifier(tmp_path: Path):
    """build_offline_bundle creates bundle directory and bundle_verify CLI passes on untampered bundle."""
    # Seed simple ledger events
    emit("WORK_ITEM_CREATED", "work_item", "wi1", {"title": "x"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    bundle_dir = tmp_path / "bundle"
    index = build_offline_bundle(tmp_path, bundle_dir, include_artifacts=False)
    assert (bundle_dir / "bundle.json").exists()
    assert index["contents"]["ledger_events_count"] >= 1
    # Run bundle_verify CLI
    from tools import bundle_verify as bv

    report = bv.verify_bundle(bundle_dir)
    assert report["ok"] is True


def test_governance_ux_batching_and_fatigue(tmp_path: Path):
    """Approval batching events and fatigue + spotcheck lifecycle."""
    items = [
        {"id": "a1", "risk_score": 0.1},
        {"id": "a2", "risk_score": 0.9},
        {"id": "a3", "risk_score": 0.5},
    ]
    ranked = rank_approvals_by_risk(items)
    assert ranked[0]["id"] == "a2"
    batch_id, _ = create_approval_batch(
        items=ranked,
        scope=SCOPE,
        actor=ACTOR,
        rationale="low-risk batch",
        workspace_root=tmp_path,
    )
    record_approval_batch_approved(batch_id=batch_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_fatigue_limit_reached(
        operator_id="op1",
        window_minutes=60,
        approvals_in_window=120,
        limit=100,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    _ev_id, spot_id = request_audit_spotcheck(
        target_id="a2",
        reason="random_sample",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    record_audit_spotcheck_completed(
        spotcheck_id=spot_id,
        outcome="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "APPROVAL_BATCH_CREATED" in actions
    assert "APPROVAL_BATCH_APPROVED" in actions
    assert "APPROVAL_FATIGUE_LIMIT_REACHED" in actions
    assert "AUDIT_SPOTCHECK_REQUESTED" in actions
    assert "AUDIT_SPOTCHECK_COMPLETED" in actions


def test_policy_diff_risk(tmp_path: Path):
    """POLICY_DIFF_RISK_REPORT artifact and event; loosening controls yields higher risk and should_block."""
    old_p = tmp_path / "old_policy.json"
    new_p = tmp_path / "new_policy.json"
    old_p.write_text(
        json.dumps(
            {
                "permissions": ["read"],
                "restrictions": ["no_production"],
                "threshold": 0.8,
            }
        ),
        encoding="utf-8",
    )
    new_p.write_text(
        json.dumps(
            {
                "permissions": ["read", "write"],
                "restrictions": [],
                "threshold": 0.5,
            }
        ),
        encoding="utf-8",
    )
    report = compute_policy_diff_risk(
        old_policy_path=old_p,
        new_policy_path=new_p,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        block_threshold=0.5,
    )
    assert report["score"] >= 0.5
    assert report["should_block"] is True
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "POLICY_DIFF_RISK_REPORT" in actions

