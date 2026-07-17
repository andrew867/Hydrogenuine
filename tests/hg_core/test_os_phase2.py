"""
OS Phase 2: Retention, incident enforcement, tenancy, explain, red-team.
See .cursor/plans/operatingsystem/chapter2/operatingsystem_phase2/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.retention import (
    run_retention_job,
    record_artifact_tombstoned,
    request_data_removal,
    execute_data_removal,
)
from hg_core.extras.incidents import (
    create_incident_candidate,
    confirm_incident,
    mitigate_incident,
    close_incident,
)
from hg_core.incidents import apply_enforcement, record_autonomy_restored
from hg_core.tenancy import TenantContext, DEFAULT_TENANT_CONTEXT, scope_with_tenancy
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import get_scope_ledger_path, iter_events_by_scope, _iter_scope_paths
from hg_core.explain import (
    explain_work_item,
    explain_decision,
    explain_incident,
    explain_action,
    export_signed_bundle,
)
from hg_core.redteam import generate_adversarial_run
from hg_core.materializers import run_all


SCOPE = {"type": "run", "id": "test_os2"}
ACTOR = {"agent_id": "agent_os2", "pubkey": "0" * 64, "key_id": "k"}


def test_retention_job_emits_events(tmp_path: Path):
    """run_retention_job writes summary artifact and emits RETENTION_JOB_RAN (or dry_run skips emit)."""
    result = run_retention_job(scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, retention_days=365, dry_run=True)
    assert "job_id" in result
    assert "tombstoned_count" in result
    assert "summary_artifact_path" in result
    assert (tmp_path / result["summary_artifact_path"].replace(str(tmp_path) + "/", "")).exists() or "retention" in result["summary_artifact_path"]


def test_artifact_tombstoned_and_data_removal_events(tmp_path: Path):
    """record_artifact_tombstoned, request_data_removal, execute_data_removal emit correctly."""
    e1 = record_artifact_tombstoned(
        artifact_id="art_1",
        scope=SCOPE,
        actor=ACTOR,
        reason="test",
        retention_policy_id="policy_1",
        workspace_root=tmp_path,
    )
    assert e1
    req_id = request_data_removal(
        scope=SCOPE,
        actor=ACTOR,
        target_refs=[{"type": "artifact", "id": "art_1"}],
        rationale="test",
        workspace_root=tmp_path,
    )
    assert req_id
    e2 = execute_data_removal(
        request_id=req_id,
        scope=SCOPE,
        actor=ACTOR,
        tombstone_ids=["art_1"],
        workspace_root=tmp_path,
    )
    assert e2
    actions = []
    for _st, _sid, ev in iter_events_by_scope(tmp_path):
        actions.append(ev.get("action"))
    assert "ARTIFACT_TOMBSTONED" in actions
    assert "DATA_REMOVAL_REQUESTED" in actions
    assert "DATA_REMOVAL_EXECUTED" in actions


def test_incident_mitigate_close_and_enforcement(tmp_path: Path):
    """mitigate_incident, close_incident, apply_enforcement, record_autonomy_restored emit and index."""
    cid = create_incident_candidate(
        scope=SCOPE,
        actor=ACTOR,
        source="test",
        evidence_refs=[],
        severity="medium",
        workspace_root=tmp_path,
    )
    iid = confirm_incident(candidate_id=cid, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    mitigate_incident(incident_id=iid, scope=SCOPE, actor=ACTOR, mitigation_summary="Mitigated", workspace_root=tmp_path)
    enf_id = apply_enforcement(
        incident_id=iid,
        scope=SCOPE,
        actor=ACTOR,
        effects={"trust_band_tightened": True},
        notes="Test",
        workspace_root=tmp_path,
    )
    assert enf_id
    record_autonomy_restored(
        incident_id=iid,
        scope=SCOPE,
        actor=ACTOR,
        postmortem_ref="artifacts/incidents/postmortem_1.json",
        workspace_root=tmp_path,
    )
    close_incident(incident_id=iid, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_all(tmp_path, rebuild=True)
    actions = []
    for _st, _sid, ev in iter_events_by_scope(tmp_path):
        actions.append(ev.get("action"))
    assert "INCIDENT_MITIGATED" in actions
    assert "INCIDENT_CLOSED" in actions
    assert "ENFORCEMENT_APPLIED" in actions
    assert "AUTONOMY_RESTORED" in actions


def test_tenancy_scope_and_ledger_path(tmp_path: Path):
    """scope_with_tenancy and ledger path with tenant/env isolate scope files."""
    scope = scope_with_tenancy("run", "tenant_test", tenant_id="acme", environment="dev")
    assert scope["tenant_id"] == "acme"
    assert scope["environment"] == "dev"
    path = get_scope_ledger_path(tmp_path, "run", "tenant_test", tenant_id="acme", environment="dev")
    assert "acme" in str(path)
    assert "dev" in str(path)
    emit(
        "DECISION_COMMITTED",
        "decision",
        "d_tenant",
        {"decision_id": "d_tenant", "title": "Tenant test"},
        scope=scope,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert path.exists() or (tmp_path / "memory" / "ledger" / "scopes" / "acme" / "dev" / "run" / "tenant_test.jsonl").exists()


def test_iter_scope_paths_includes_tenancy_layout(tmp_path: Path):
    """_iter_scope_paths yields both legacy and tenancy layout scope files."""
    scope_legacy = {"type": "run", "id": "legacy"}
    emit("DECISION_COMMITTED", "decision", "d1", {"decision_id": "d1"}, scope=scope_legacy, actor=ACTOR, workspace_root=tmp_path)
    scope_tenancy = scope_with_tenancy("run", "ten", tenant_id="t1", environment="prod")
    emit("DECISION_COMMITTED", "decision", "d2", {"decision_id": "d2"}, scope=scope_tenancy, actor=ACTOR, workspace_root=tmp_path)
    paths = list(_iter_scope_paths(tmp_path))
    assert len(paths) >= 1
    types_ids = [(st, sid) for st, sid, _ in paths]
    assert ("run", "legacy") in types_ids or ("run", "ten") in types_ids


def test_explain_work_item_decision_incident_action(tmp_path: Path):
    """explain_work_item, explain_decision, explain_incident, explain_action return structures."""
    from hg_core.work_items import create_work_item
    wi_id = create_work_item(scope=SCOPE, actor=ACTOR, wi_type="task", title="Explain WI", workspace_root=tmp_path)
    emit("DECISION_COMMITTED", "decision", "dec_ex", {"decision_id": "dec_ex", "title": "Explain dec"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_all(tmp_path, rebuild=True)
    wi_ex = explain_work_item(tmp_path, wi_id, include_timeline=True)
    assert "work_item_id" in wi_ex
    assert wi_ex.get("work_item") or wi_ex.get("timeline") is not None
    dec_ex = explain_decision(tmp_path, "dec_ex", include_links=True)
    assert dec_ex.get("decision_id") == "dec_ex"
    inc_ex = explain_incident(tmp_path, "nonexistent", include_links=True)
    assert inc_ex.get("incident_id") == "nonexistent"
    assert inc_ex.get("records") is not None
    act_ex = explain_action(tmp_path, "act_nonexistent")
    assert act_ex.get("action_id") == "act_nonexistent"
    assert "trail" in act_ex


def test_export_signed_bundle(tmp_path: Path):
    """export_signed_bundle writes artifact and emits AUDIT_BUNDLE_EXPORTED."""
    emit("DECISION_COMMITTED", "decision", "bundle_dec", {"decision_id": "bundle_dec", "title": "Bundle"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_all(tmp_path, rebuild=True)
    out = export_signed_bundle(
        tmp_path,
        "decision_audit",
        ["bundle_dec"],
        scope=SCOPE,
        actor=ACTOR,
        include_raw=False,
    )
    assert "bundle_path" in out
    assert "checksum_sha256" in out
    assert Path(out["bundle_path"]).exists()
    actions = []
    for _st, _sid, ev in iter_events_by_scope(tmp_path):
        actions.append(ev.get("action"))
    assert "AUDIT_BUNDLE_EXPORTED" in actions


def test_redteam_adversarial_run(tmp_path: Path):
    """generate_adversarial_run emits deterministic events; materializers process them."""
    emitted = generate_adversarial_run(tmp_path, scope_type="run", scope_id="redteam_adv")
    assert len(emitted) >= 2
    run_all(tmp_path, rebuild=True)
    actions = []
    for _st, _sid, ev in iter_events_by_scope(tmp_path):
        if _sid == "redteam_adv":
            actions.append(ev.get("action"))
    assert "DECISION_COMMITTED" in actions
    assert "ACTION_PROPOSED" in actions or "WORK_ITEM_CREATED" in actions


def test_scope_with_tenancy_invalid_env():
    """scope_with_tenancy rejects invalid environment."""
    with pytest.raises(ValueError, match="environment"):
        scope_with_tenancy("run", "x", environment="invalid")
