"""
Ch7 Completeness extras: event taxonomy, policy center, incidents, search/cross-link, rebuild/verify, audit, retention.
See .cursor/plans/stickyreality/chapter7/sticky_reality_complete_extras/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.extras import (
    load_event_taxonomy,
    get_action_meta,
    list_actions,
    list_policy_artifacts,
    get_active_policy_set,
    publish_policy,
    record_policy_applied,
    apply_policy_override,
    create_incident_candidate,
    confirm_incident,
    resolve_incident,
    record_corrective_action_tracked,
    record_policy_change_linked,
    build_search_index,
    search,
    get_decision_links,
    get_anomaly_links,
    rebuild_all_materializers,
    verify_ledger_chain,
    verify_artifact_checksums,
    get_materializer_status,
    emit_audit_event,
    list_audit_events,
    export_audit_bundle,
    record_tombstone,
    list_artifacts_for_retention,
)
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers import run_all as run_all_materializers
from hg_core.materializers.extras_indexer import run as run_extras_indexer
from hg_core.social import create_handoff
from hg_core.affective import apply_modulation
from hg_core.metacognition import record_self_assessment
from hg_core.temporal import start_episode, end_episode


SCOPE = {"type": "run", "id": "test_run"}
ACTOR = {"agent_id": "agent_A", "pubkey": "0" * 64, "key_id": "k"}


def test_event_taxonomy_load_and_meta(tmp_path: Path):
    """load_event_taxonomy returns default when no file; get_action_meta and list_actions work."""
    tax = load_event_taxonomy(tmp_path)
    assert "actions" in tax
    meta = get_action_meta(tax, "DECISION_COMMITTED")
    assert meta is not None
    assert meta.get("severity") == "state"
    actions = list_actions(tax)
    assert "OBSERVATION_RECORDED" in actions or "DECISION_COMMITTED" in actions


def test_policy_center_list_and_active(tmp_path: Path):
    """list_policy_artifacts and get_active_policy_set return policy data."""
    arts = list_policy_artifacts(tmp_path)
    assert isinstance(arts, list)
    active = get_active_policy_set(tmp_path, "run", "test_run")
    assert "trust_and_budget" in active
    assert "regulatory" in active


def test_publish_policy_emits(tmp_path: Path):
    """publish_policy emits POLICY_PUBLISHED."""
    eid = publish_policy(
        policy_type="trust_and_budget",
        artifact_path="artifacts/policy/trust_and_budget_policy.yaml",
        version="1.0",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "POLICY_PUBLISHED" for _, _, ev in evs)


def test_record_policy_applied_emits(tmp_path: Path):
    """record_policy_applied emits POLICY_APPLIED."""
    eid = record_policy_applied(scope=SCOPE, policy_ref="pol_abc", actor=ACTOR, workspace_root=tmp_path)
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "POLICY_APPLIED" for _, _, ev in evs)


def test_apply_policy_override_requires_expiry(tmp_path: Path):
    """apply_policy_override requires expiry_ts."""
    with pytest.raises(ValueError, match="expiry_ts"):
        apply_policy_override(
            scope=SCOPE,
            override_spec={"allow": "WRITE"},
            expiry_ts="",
            actor=ACTOR,
            rationale="Test",
            workspace_root=tmp_path,
        )
    eid = apply_policy_override(
        scope=SCOPE,
        override_spec={"allow": "WRITE"},
        expiry_ts="2027-01-01Z",
        actor=ACTOR,
        rationale="Test",
        workspace_root=tmp_path,
    )
    assert eid


def test_incident_candidate_and_confirm_resolve(tmp_path: Path):
    """create_incident_candidate, confirm_incident, resolve_incident (with postmortem for medium+)."""
    cid = create_incident_candidate(
        scope=SCOPE,
        actor=ACTOR,
        source="anomaly",
        evidence_refs=[{"type": "decision", "id": "dec_1"}],
        severity="medium",
        summary="Test incident",
        workspace_root=tmp_path,
    )
    assert cid
    confirm_incident(candidate_id=cid, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    with pytest.raises(ValueError, match="postmortem_ref"):
        resolve_incident(
            incident_id=cid,
            scope=SCOPE,
            actor=ACTOR,
            severity="medium",
            workspace_root=tmp_path,
        )
    eid = resolve_incident(
        incident_id=cid,
        scope=SCOPE,
        actor=ACTOR,
        postmortem_ref="pm_1",
        severity="medium",
        workspace_root=tmp_path,
    )
    assert eid


def test_corrective_action_and_policy_change_linked(tmp_path: Path):
    """record_corrective_action_tracked and record_policy_change_linked emit."""
    create_incident_candidate(scope=SCOPE, actor=ACTOR, source="test", evidence_refs=[], workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    cid = next(ev["payload"]["candidate_id"] for _, _, ev in evs if ev.get("action") == "INCIDENT_CANDIDATE_CREATED")
    confirm_incident(candidate_id=cid, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_corrective_action_tracked(incident_id=cid, action_ref="fix_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_policy_change_linked(incident_id=cid, policy_ref="pol_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    evs2 = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "CORRECTIVE_ACTION_TRACKED" for _, _, ev in evs2)
    assert any(ev.get("action") == "POLICY_CHANGE_LINKED" for _, _, ev in evs2)


def test_build_search_index_and_search(tmp_path: Path):
    """build_search_index and search return results from materialized data."""
    emit(
        "DECISION_COMMITTED",
        "decision",
        "d1",
        {"decision_id": "d1", "title": "Test decision", "based_on_claim_ids": []},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    idx = build_search_index(tmp_path)
    assert isinstance(idx, list)
    results = search(tmp_path, "Test", type_filter="decision", limit=10)
    assert isinstance(results, list)


def test_get_decision_links_and_anomaly_links(tmp_path: Path):
    """get_decision_links and get_anomaly_links return cross-link dicts."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True)
    (root / "bindings.jsonl").write_text("")
    (root / "self_assessments.jsonl").write_text("")
    (root / "anomalies.jsonl").write_text("")
    (root / "incidents.jsonl").write_text("")
    emit(
        "DECISION_COMMITTED",
        "decision",
        "dec_1",
        {"decision_id": "dec_1", "title": "Decision 1", "based_on_claim_ids": []},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    links = get_decision_links(tmp_path, "dec_1")
    assert "decision_id" in links
    assert "claims" in links
    anomaly_links = get_anomaly_links(tmp_path, "anom_1")
    assert "anomaly_id" in anomaly_links
    assert "observation_ids" in anomaly_links


def test_rebuild_all_and_verify_and_status(tmp_path: Path):
    """rebuild_all_materializers, verify_ledger_chain, get_materializer_status run without error."""
    rebuild_all_materializers(tmp_path)
    report = verify_ledger_chain(tmp_path)
    assert "ok" in report
    status = get_materializer_status(tmp_path)
    assert "materializers" in status
    art_report = verify_artifact_checksums(tmp_path, limit=10)
    assert "ok" in art_report
    assert "checked" in art_report


def test_emit_audit_event(tmp_path: Path):
    """emit_audit_event emits PRIVILEGED_ACCESS."""
    eid = emit_audit_event(action="view_sensitive", resource="obs_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "PRIVILEGED_ACCESS" for _, _, ev in evs)


def test_export_audit_bundle_emits(tmp_path: Path):
    """export_audit_bundle writes artifact and emits AUDIT_BUNDLE_EXPORTED."""
    emit_audit_event(action="pre", resource="r", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_extras_indexer(tmp_path, rebuild=True)
    eid = export_audit_bundle(workspace_root=tmp_path, scope=SCOPE, actor=ACTOR)
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "AUDIT_BUNDLE_EXPORTED" for _, _, ev in evs)
    assert (tmp_path / "artifacts" / "audit").exists()


def test_list_audit_events(tmp_path: Path):
    """list_audit_events returns rows from materialized audit_events.jsonl."""
    emit_audit_event(action="test", resource="r1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_extras_indexer(tmp_path, rebuild=True)
    events = list_audit_events(tmp_path)
    assert isinstance(events, list)


def test_record_tombstone_emits(tmp_path: Path):
    """record_tombstone emits TOMBSTONE_RECORDED."""
    eid = record_tombstone(scope=SCOPE, actor=ACTOR, artifact_path="artifacts/obs/raw/x.json", workspace_root=tmp_path)
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "TOMBSTONE_RECORDED" for _, _, ev in evs)


def test_list_artifacts_for_retention(tmp_path: Path):
    """list_artifacts_for_retention returns paths under artifacts/."""
    (tmp_path / "artifacts" / "policy").mkdir(parents=True)
    (tmp_path / "artifacts" / "policy" / "x.yaml").write_text("x")
    out = list_artifacts_for_retention(tmp_path)
    assert isinstance(out, list)


def test_extras_indexer_produces_files(tmp_path: Path):
    """Extras indexer produces incidents.jsonl, policy_events.jsonl, audit_events.jsonl."""
    create_incident_candidate(scope=SCOPE, actor=ACTOR, source="test", evidence_refs=[], workspace_root=tmp_path)
    publish_policy(policy_type="regulatory", artifact_path="artifacts/policy/reg.yaml", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    emit_audit_event(action="view", resource="r", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_extras_indexer(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "incidents.jsonl").exists()
    assert (root / "policy_events.jsonl").exists()
    assert (root / "audit_events.jsonl").exists()


def test_e2e_sticky_reality_full_flow(tmp_path: Path):
    """E2E: synthetic run across all Sticky Reality domains, rebuild all materializers, verify, export audit bundle."""
    # Ch1/ledger: decision event (feeds decision + molecules materializers)
    emit(
        "DECISION_COMMITTED",
        "decision",
        "dec_e2e_1",
        {"title": "E2E decision", "based_on_claim_ids": []},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    # Ch2: observation (observations indexer)
    emit(
        "OBSERVATION_RECORDED",
        "observation",
        "obs_e2e_1",
        {"observation_id": "obs_e2e_1", "signal_id": "sig_1", "pii_class": "none", "payload_ref": {}},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    # Ch3: self-assessment (metacognition)
    record_self_assessment(
        decision_id="dec_e2e_1",
        confidence=0.8,
        uncertainty_factors=[],
        risk_flags=[],
        recommended_controls={"require_approval": False, "slow_mode": False},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    # Ch4: episode (temporal)
    episode_id = start_episode(name="e2e_episode", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    end_episode(episode_id=episode_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    # Ch5: handoff (social)
    create_handoff(
        from_agent_id="A",
        to_agent_id="B",
        work_item_ref={"type": "decision", "id": "dec_e2e_1"},
        ownership_mode="delegate",
        expected_response_by="2027-12-31Z",
        priority="normal",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    # Ch6: modulation (affective)
    apply_modulation(
        scope=SCOPE,
        actor=ACTOR,
        before_state={"trust_band": 0},
        after_state={"trust_band": 1},
        workspace_root=tmp_path,
    )
    # Ch7: incident, policy, audit (extras)
    create_incident_candidate(
        scope=SCOPE, actor=ACTOR, source="e2e", evidence_refs=[{"type": "decision", "id": "dec_e2e_1"}], workspace_root=tmp_path
    )
    publish_policy(
        policy_type="trust_and_budget",
        artifact_path="artifacts/policy/trust_and_budget_policy.yaml",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    emit_audit_event(action="e2e_audit", resource="e2e", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    # Rebuild all materializers
    run_all_materializers(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "decisions.jsonl").exists()
    assert (root / "observations.jsonl").exists()
    assert (root / "self_assessments.jsonl").exists()
    assert (root / "episodes.jsonl").exists()
    assert (root / "handoffs.jsonl").exists()
    assert (root / "applied_modulations.jsonl").exists()
    assert (root / "incidents.jsonl").exists()
    assert (root / "policy_events.jsonl").exists()
    assert (root / "audit_events.jsonl").exists()
    # Verify and status
    report = verify_ledger_chain(tmp_path)
    assert report.get("ok") is True
    status = get_materializer_status(tmp_path)
    assert "materializers" in status
    # Export audit bundle and assert event emitted
    eid = export_audit_bundle(workspace_root=tmp_path, scope=SCOPE, actor=ACTOR)
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "AUDIT_BUNDLE_EXPORTED" for _, _, ev in evs)
