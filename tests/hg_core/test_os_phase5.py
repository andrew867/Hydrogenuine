"""
OS Phase 5: Compliance, IAM, DLP, Plugins, HA/DR.
See .cursor/plans/operatingsystem/chapter5/operatingsystem_phase5/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.compliance import (
    publish_attestation,
    run_control_check,
    request_audit_export,
    complete_audit_export,
    list_attestations,
)
from hg_core.iam import (
    validate_oidc_claims,
    get_roles_for_principal,
    check_permission,
    resolve_approvers_for_action,
    load_oidc_config,
    load_rbac_config,
    record_privileged_access,
)
from hg_core.dlp import (
    run_dlp_scan,
    quarantine_artifact,
    release_from_quarantine,
    apply_legal_hold,
    release_legal_hold,
    record_key_rotated,
)
from hg_core.plugins import (
    load_plugin_manifest,
    register_plugin,
    enable_plugin,
    disable_plugin,
    list_plugins,
    check_plugin_capability,
)
from hg_core.reliability import get_ha_status, record_backup_completed
from hg_gateway.db import get_connection


SCOPE = {"type": "run", "id": "test_os5"}
ACTOR = {"agent_id": "agent_os5", "pubkey": "0" * 64, "key_id": "k"}


def test_compliance_attestation_and_control_check(tmp_path: Path):
    """ATTESTATION_PUBLISHED, CONTROL_CHECK_RAN; list_attestations."""
    aid = publish_attestation(
        tenant_id="t1",
        environment="prod",
        scope=SCOPE,
        actor=ACTOR,
        attestation_content={"policies_active": ["p1"], "effective_dates": "2026-01-01"},
        workspace_root=tmp_path,
    )
    assert aid.startswith("att_")
    run_control_check(
        scope=SCOPE,
        actor=ACTOR,
        check_name="retention_ran",
        result="pass",
        summary={"jobs": 1},
        workspace_root=tmp_path,
    )
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "ATTESTATION_PUBLISHED" in actions
    assert "CONTROL_CHECK_RAN" in actions
    listed = list_attestations(tmp_path, tenant_id="t1", environment="prod")
    assert any(a.get("attestation_id") == aid for a in listed)


def test_audit_export_requested_completed(tmp_path: Path):
    """AUDIT_EXPORT_REQUESTED, AUDIT_EXPORT_COMPLETED."""
    rid = request_audit_export(scope=SCOPE, actor=ACTOR, reason="legal", workspace_root=tmp_path)
    assert rid
    bundle_path = tmp_path / "artifacts" / "bundles" / "audit_1.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("{}")
    complete_audit_export(
        request_id=rid,
        scope=SCOPE,
        actor=ACTOR,
        bundle_artifact_id=str(bundle_path),
        workspace_root=tmp_path,
    )
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "AUDIT_EXPORT_REQUESTED" in actions
    assert "AUDIT_EXPORT_COMPLETED" in actions


def test_iam_oidc_rbac(tmp_path: Path):
    """validate_oidc_claims, get_roles_for_principal, check_permission, resolve_approvers, PRIVILEGED_ACCESS."""
    (tmp_path / "artifacts" / "iam").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "iam" / "oidc_config.json").write_text(
        json.dumps({"issuer": "https://idp.example.com", "audience": "hg", "require_issuer": True}),
        encoding="utf-8",
    )
    (tmp_path / "artifacts" / "iam" / "rbac.json").write_text(
        json.dumps({
            "role_permissions": {"admin": ["*"], "operator": ["read", "approve"]},
            "principal_roles": {"t1": {"user1": ["operator"]}},
        }),
        encoding="utf-8",
    )
    (tmp_path / "artifacts" / "iam" / "approval_routing.json").write_text(
        json.dumps({"by_action": {"policy_publish": ["admin"], "high_impact": ["admin", "reviewer"]}}),
        encoding="utf-8",
    )
    invalid = validate_oidc_claims({"sub": "u1", "iss": "wrong"}, workspace_root=tmp_path)
    assert invalid is None
    valid = validate_oidc_claims({"sub": "u1", "iss": "https://idp.example.com", "aud": "hg"}, workspace_root=tmp_path)
    assert valid is not None and valid.get("sub") == "u1"
    roles = get_roles_for_principal("t1", "user1", workspace_root=tmp_path)
    assert "operator" in roles
    assert check_permission("user1", ["operator"], "approve", "action", workspace_root=tmp_path) is True
    assert check_permission("user1", ["viewer"], "approve", "action", workspace_root=tmp_path) is False
    approvers = resolve_approvers_for_action("t1", "policy_publish", workspace_root=tmp_path)
    assert "admin" in approvers
    record_privileged_access(scope=SCOPE, actor=ACTOR, action="override", resource="policy_x", workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "PRIVILEGED_ACCESS" in actions


def test_dlp_scan_quarantine_legal_hold(tmp_path: Path):
    """DLP_SCAN_COMPLETED, DATA_QUARANTINED, DATA_RELEASED, LEGAL_HOLD_APPLIED/RELEASED, KEY_ROTATED."""
    art = tmp_path / "artifacts" / "sample.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text('{"note": "clean"}')
    result, _ = run_dlp_scan(
        artifact_path=art,
        artifact_id="art_1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert result in ("pass", "warn", "fail")
    quarantine_artifact(artifact_id="art_1", scope=SCOPE, actor=ACTOR, reason="dlp_fail", workspace_root=tmp_path)
    release_from_quarantine(artifact_id="art_1", scope=SCOPE, actor=ACTOR, reason="cleared", workspace_root=tmp_path)
    apply_legal_hold(artifact_ref="art_1", scope=SCOPE, actor=ACTOR, reason="litigation", workspace_root=tmp_path)
    # release uses a hold_id; in real flow use the id from apply_legal_hold payload
    release_legal_hold(hold_id="hold_art_1", scope=SCOPE, actor=ACTOR, reason="released", workspace_root=tmp_path)
    record_key_rotated(key_id="key_1", scope=SCOPE, actor=ACTOR, tenant_id="t1", workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "DLP_SCAN_COMPLETED" in actions
    assert "DATA_QUARANTINED" in actions
    assert "DATA_RELEASED" in actions
    assert "LEGAL_HOLD_APPLIED" in actions
    assert "LEGAL_HOLD_RELEASED" in actions
    assert "KEY_ROTATED" in actions


def test_dlp_scan_fail_on_pii(tmp_path: Path):
    """DLP scan returns fail when placeholder PII pattern present."""
    art = tmp_path / "artifacts" / "pii.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text('{"ssn": "123-45-6789"}')
    result, _ = run_dlp_scan(
        artifact_path=art,
        artifact_id="art_pii",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert result == "fail"


def test_plugins_install_enable_disable(tmp_path: Path):
    """load_plugin_manifest, register_plugin, PLUGIN_INSTALLED, enable/disable, list_plugins, check_plugin_capability."""
    manifest_path = tmp_path / "plugin_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "plugin_id": "test_plugin",
            "name": "Test",
            "version": "1.0.0",
            "capabilities": ["observe", "anomaly_rule"],
            "signature": "sig123",
        }),
        encoding="utf-8",
    )
    m = load_plugin_manifest(manifest_path)
    assert m["plugin_id"] == "test_plugin"
    register_plugin(manifest_path=manifest_path, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    disable_plugin(plugin_id="test_plugin", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    enable_plugin(plugin_id="test_plugin", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    actions = [ev.get("action") for _st, _sid, ev in iter_events_by_scope(tmp_path)]
    assert "PLUGIN_INSTALLED" in actions
    assert "PLUGIN_ENABLED" in actions
    assert "PLUGIN_DISABLED" in actions
    plugins = list_plugins(tmp_path, enabled_only=True)
    assert any(p["plugin_id"] == "test_plugin" for p in plugins)
    assert check_plugin_capability(tmp_path, "test_plugin", "observe") is True
    assert check_plugin_capability(tmp_path, "test_plugin", "nonexistent") is False


def test_plugin_manifest_validation(tmp_path: Path):
    """load_plugin_manifest raises on missing required fields."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"plugin_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required field"):
        load_plugin_manifest(bad)


def test_ha_status_and_backup(tmp_path: Path):
    """get_ha_status returns ledger_ok, materializer_lag, last_backup_ts; record_backup_completed updates last_backup."""
    emit("WORK_ITEM_CREATED", "work_item", "wi_1", {"title": "x"}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    status = get_ha_status(tmp_path)
    assert "ledger_ok" in status
    assert "ts" in status
    record_backup_completed(tmp_path, backup_id="b1")
    status2 = get_ha_status(tmp_path)
    assert status2.get("last_backup_ts") is not None
    with get_connection(str(tmp_path / "memory" / "gateway.sqlite3")) as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM artifact_registry_entries
            WHERE class_key = ? AND file_path = ?
            """,
            ("backup", "artifacts/backups/last_backup.json"),
        ).fetchone()
        assert row is not None


def test_backup_runbook_script(tmp_path: Path):
    """ops/backup_runbook.run_backup writes manifest and last_backup."""
    from ops.backup_runbook import run_backup
    manifest = run_backup(tmp_path, backup_id="drill_1")
    assert "ledger_paths" in manifest
    last = tmp_path / "artifacts" / "backups" / "last_backup.json"
    assert last.exists()
    data = json.loads(last.read_text(encoding="utf-8"))
    assert data.get("backup_id") == "drill_1"
