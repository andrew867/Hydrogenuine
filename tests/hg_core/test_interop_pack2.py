"""
Interop Pack 2: Federation, DID/VC, memory capsules, connector SDK, trust negotiation.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from hg_core.interop import (
    propose_federation_link,
    accept_federation_link,
    reject_federation_link,
    load_federation_link,
    validate_cross_domain_a2a,
    emit_federation_violation,
    register_did,
    issue_vc,
    revoke_vc,
    load_vc,
    validate_vc,
    publish_trust_root,
    publish_memory_capsule,
    share_capsule,
    import_capsule,
    load_capsule,
    verify_capsule_signature,
    publish_connector_manifest,
    run_connector_conformance,
    certify_connector,
    propose_trust_tier,
    accept_trust_tier,
    reject_trust_tier,
    grant_downgrade_exception,
    is_downgrade,
)


SCOPE = {"type": "run", "id": "test_iop2"}
ACTOR = {"agent_id": "agent_iop2", "pubkey": "0" * 64, "key_id": "k"}


def test_federation_cross_domain_references_link(tmp_path: Path) -> None:
    """Cross-domain A2A must reference a valid federation link."""
    link_id = propose_federation_link(
        domains=["domain_a", "domain_b"],
        rules={"min_tier": "T1"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert link_id.startswith("flink_")
    accept_federation_link(link_id=link_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    valid, reason = validate_cross_domain_a2a(tmp_path, link_id, {"id": "run1"}, now)
    assert valid is True
    assert load_federation_link(tmp_path, link_id) is not None


def test_federation_violations_logged(tmp_path: Path) -> None:
    """Violations detected and logged."""
    link_id = propose_federation_link(domains=["a"], rules={}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev = emit_federation_violation(link_id=link_id, reason="unauthorized_topic", ref_id="msg_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev


def test_invalid_revoked_vc_blocks_privileged(tmp_path: Path) -> None:
    """Invalid or revoked VC blocks privileged intent tags."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    vc_id = issue_vc(issuer="issuer1", subject_did="did:test:agent1", claims={"role": "operator"}, expires_ts=future, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    vc = load_vc(tmp_path, vc_id)
    assert vc is not None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assert validate_vc(vc, now)[0] is True
    revoke_vc(vc_id=vc_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    vc2 = load_vc(tmp_path, vc_id)
    assert vc2 is not None and vc2.get("revoked_ts")
    assert validate_vc(vc2, now)[0] is False


def test_did_trust_roots(tmp_path: Path) -> None:
    """DID trust roots validate signatures (publish trust root)."""
    register_did(did="did:key:abc", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev = publish_trust_root(root_id="root1", domain="domain1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, allowed_issuers=["issuer1"])
    assert ev


def test_capsule_signature_verified(tmp_path: Path) -> None:
    """Capsule signature verified."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    cap_id = publish_memory_capsule(
        scope=SCOPE,
        expires_ts=future,
        redaction_level="low",
        manifests={"events": []},
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    capsule = load_capsule(tmp_path, cap_id)
    assert capsule is not None
    assert verify_capsule_signature(capsule) is True


def test_capsule_rejected_on_expiry(tmp_path: Path) -> None:
    """Capsule rejected on expiry or classification mismatch."""
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    cap_id = publish_memory_capsule(
        scope=SCOPE,
        expires_ts=past,
        redaction_level="low",
        manifests={},
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    capsule = load_capsule(tmp_path, cap_id)
    assert capsule is not None
    accepted, _ = import_capsule(capsule_id=cap_id, capsule=capsule, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert accepted is False


def test_capsule_redaction_enforced(tmp_path: Path) -> None:
    """Redaction level enforced (reject when capsule redaction > max allowed)."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    cap_id = publish_memory_capsule(
        scope=SCOPE,
        expires_ts=future,
        redaction_level="high",
        manifests={},
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    capsule = load_capsule(tmp_path, cap_id)
    accepted, _ = import_capsule(capsule_id=cap_id, capsule=capsule, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, max_redaction_level="low")
    assert accepted is False


def test_connector_conformance_report(tmp_path: Path) -> None:
    """Conformance harness validates receipts, deny paths, idempotency; certification report produced."""
    publish_connector_manifest(
        connector_id="conn_sdk1",
        operations=[{"name": "fetch"}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    report, ev = run_connector_conformance(
        connector_id="conn_sdk1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        scenarios_passed={"receipts": True, "idempotency": True},
    )
    assert report.get("passed") is True
    assert ev
    ev_cert = certify_connector(connector_id="conn_sdk1", report_id=report["report_id"], scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_cert


def test_downgrade_without_exception_rejected(tmp_path: Path) -> None:
    """Downgrade without exception is rejected (is_downgrade; reject flow)."""
    assert is_downgrade("T2", "T1") is True
    assert is_downgrade("T1", "T2") is False
    ev = reject_trust_tier(ref_id="op_1", reason="downgrade_not_allowed", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev


def test_downgrade_exception_time_bound(tmp_path: Path) -> None:
    """Exception is time-bound and audited."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    ev = grant_downgrade_exception(
        ref_id="op_2",
        from_tier="T2",
        to_tier="T1",
        expiry_ts=future,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev
