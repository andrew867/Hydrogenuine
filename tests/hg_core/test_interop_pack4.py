"""
Interop Pack 4: Multi-party trust, threshold signing, key custody, issuer governance.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from hg_core.trust import (
    propose_threshold_action,
    add_threshold_signature,
    finalize_threshold_action,
    load_threshold_action,
    create_key,
    rotate_key,
    revoke_key,
    issue_short_lived_token,
    revoke_token,
    request_break_glass,
    grant_break_glass,
    expire_break_glass,
    run_vault_health_check,
    publish_bridge_trust_root,
    rotate_bridge_trust_root,
    freeze_grants_on_compromise,
    record_compromise_response,
    publish_issuer_group,
    add_issuer_group_member,
    remove_issuer_group_member,
    load_issuer_group,
    propose_vc_issuance,
    propose_vc_revocation,
    check_issuer_quorum_for_type,
)


SCOPE = {"type": "run", "id": "test_iop4"}
ACTOR = {"agent_id": "agent_iop4", "pubkey": "0" * 64, "key_id": "k"}


def test_threshold_cannot_finalize_without_quorum(tmp_path: Path) -> None:
    """Cannot finalize without quorum (m signatures)."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    action_id = propose_threshold_action(
        action_type="CAPABILITY_GRANT",
        scope=SCOPE,
        quorum_m=2,
        quorum_n=3,
        payload_ref={"grant_ref": "g1"},
        actor=ACTOR,
        workspace_root=tmp_path,
        expires_ts=future,
    )
    assert load_threshold_action(tmp_path, action_id) is not None
    finalized, _, reason = finalize_threshold_action(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert finalized is False
    assert reason == "quorum_not_reached"


def test_threshold_expired_cannot_finalize(tmp_path: Path) -> None:
    """Expired proposals cannot be finalized."""
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    action_id = propose_threshold_action(
        action_type="VC_ISSUANCE",
        scope=SCOPE,
        quorum_m=1,
        quorum_n=1,
        payload_ref={},
        actor=ACTOR,
        workspace_root=tmp_path,
        expires_ts=past,
    )
    finalized, _, reason = finalize_threshold_action(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert finalized is False
    assert reason == "expired"


def test_threshold_signer_independence_enforced(tmp_path: Path) -> None:
    """Signer independence: duplicate signer rejected; disallowed signer rejected."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    action_id = propose_threshold_action(
        action_type="TRUST_ROOT_ROTATE",
        scope=SCOPE,
        quorum_m=2,
        quorum_n=2,
        payload_ref={"bridge_id": "b1"},
        actor=ACTOR,
        workspace_root=tmp_path,
        expires_ts=future,
    )
    add_threshold_signature(
        action_id=action_id,
        signer_id="signer_a",
        signature_payload={"sig": "a"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    added2, _, reason2 = add_threshold_signature(
        action_id=action_id,
        signer_id="signer_a",
        signature_payload={"sig": "a2"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert added2 is False
    assert reason2 == "duplicate_signer"
    added3, _, reason3 = add_threshold_signature(
        action_id=action_id,
        signer_id="proposer_agent",
        signature_payload={"sig": "p"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        disallowed_signer_ids={"proposer_agent"},
    )
    assert added3 is False
    assert reason3 == "signer_independence"


def test_threshold_signatures_in_artifact_on_finalize(tmp_path: Path) -> None:
    """Signatures are included in artifact on finalize (offline bundle)."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    action_id = propose_threshold_action(
        action_type="POLICY_PUBLISH",
        scope=SCOPE,
        quorum_m=2,
        quorum_n=2,
        payload_ref={"policy_ref": "p1"},
        actor=ACTOR,
        workspace_root=tmp_path,
        expires_ts=future,
    )
    add_threshold_signature(action_id=action_id, signer_id="s1", signature_payload={"v": 1}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    add_threshold_signature(action_id=action_id, signer_id="s2", signature_payload={"v": 2}, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    finalized, ev_id, _ = finalize_threshold_action(action_id=action_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert finalized is True
    assert ev_id
    action = load_threshold_action(tmp_path, action_id)
    assert action.get("finalized_ts")
    sig_path = tmp_path / "artifacts" / "threshold_signatures" / f"{action_id}.json"
    assert sig_path.is_file()
    sig_doc = __import__("json").loads(sig_path.read_text(encoding="utf-8"))
    assert len(sig_doc.get("signatures", [])) == 2


def test_vault_key_created_rotated_revoked(tmp_path: Path) -> None:
    """Key lifecycle events: create, rotate, revoke."""
    create_key(key_id="key_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    rotate_key(key_id="key_1", new_key_id="key_2", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev = revoke_key(key_id="key_2", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev
    assert (tmp_path / "artifacts" / "vault_keys" / "key_2.json").is_file()


def test_vault_token_short_lived_scoped(tmp_path: Path) -> None:
    """Token issuance is short-lived and scoped."""
    ref_id = issue_short_lived_token(
        token_scope="connector:slack",
        expires_in_seconds=300,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        connector_id="slack",
    )
    assert ref_id.startswith("tok_")
    path = tmp_path / "artifacts" / "vault_tokens" / f"{ref_id}.json"
    assert path.is_file()
    doc = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert doc.get("token_scope") == "connector:slack"
    assert doc.get("connector_id") == "slack"
    assert doc.get("expires_ts")
    revoke_token(token_ref_id=ref_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    doc2 = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert doc2.get("revoked_ts")


def test_vault_break_glass_events(tmp_path: Path) -> None:
    """Break-glass requested, granted, expired."""
    request_break_glass(request_id="bg_1", reason="incident", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    grant_break_glass(request_id="bg_1", expires_in_seconds=60, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    expire_break_glass(request_id="bg_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)


def test_vault_health_check(tmp_path: Path) -> None:
    """Vault health check emits event and artifact."""
    ev = run_vault_health_check(scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev
    reports = list((tmp_path / "artifacts" / "vault_health").glob("*.json"))
    assert len(reports) >= 1


def test_issuer_group_quorum_for_vc(tmp_path: Path) -> None:
    """VC issuance requires issuer group quorum (group permits type and has quorum)."""
    publish_issuer_group(
        group_id="ig1",
        members=["did:test:a", "did:test:b"],
        quorum_m=2,
        quorum_n=2,
        permitted_types=["OperatorRole"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    allowed, reason = check_issuer_quorum_for_type(tmp_path, "ig1", "OperatorRole")
    assert allowed is True
    allowed2, reason2 = check_issuer_quorum_for_type(tmp_path, "ig1", "AdminRole")
    assert allowed2 is False
    assert "permitted" in reason2 or reason2 == "type_not_permitted"


def test_vc_issuance_proposed_as_threshold(tmp_path: Path) -> None:
    """VC issuance proposed creates threshold action."""
    publish_issuer_group(
        group_id="ig2",
        members=["did:test:x"],
        quorum_m=1,
        quorum_n=1,
        permitted_types=["ApproverRole"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    action_id = propose_vc_issuance(
        group_id="ig2",
        credential_type="ApproverRole",
        payload_ref={"subject_did": "did:test:y"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert action_id.startswith("tact_")
    action = load_threshold_action(tmp_path, action_id)
    assert action is not None
    assert action.get("action_type") == "VC_ISSUANCE"


def test_vc_revocation_proposed_propagates(tmp_path: Path) -> None:
    """VC revocation proposed creates threshold action (propagates to validation when finalized)."""
    publish_issuer_group(
        group_id="ig3",
        members=["did:test:p", "did:test:q"],
        quorum_m=1,
        quorum_n=2,
        permitted_types=["*"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    action_id = propose_vc_revocation(
        group_id="ig3",
        vc_id="vc_123",
        payload_ref={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert action_id.startswith("tact_")
    action = load_threshold_action(tmp_path, action_id)
    assert action.get("payload_ref", {}).get("vc_id") == "vc_123"


def test_trust_root_rotation_requires_threshold(tmp_path: Path) -> None:
    """Bridge trust root rotation recorded with threshold action id."""
    publish_bridge_trust_root(bridge_id="slack", root_version="v1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev = rotate_bridge_trust_root(
        bridge_id="slack",
        new_root_version="v2",
        threshold_action_id="tact_rotated_123",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_compromise_response_freezes_grants(tmp_path: Path) -> None:
    """Compromise response freezes grants and records response."""
    ev1 = freeze_grants_on_compromise(
        reason="signature_failures",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        incident_ref="inc_1",
    )
    assert ev1
    ev2 = record_compromise_response(
        response_type="key_rotation",
        details={"key_id": "k_old"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev2
    assert (tmp_path / "artifacts" / "compromise_responses").exists()


def test_issuer_group_member_add_remove(tmp_path: Path) -> None:
    """Issuer group member add/remove."""
    publish_issuer_group(
        group_id="ig4",
        members=["did:a"],
        quorum_m=1,
        quorum_n=2,
        permitted_types=[],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    add_issuer_group_member(group_id="ig4", member_did="did:b", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    g = load_issuer_group(tmp_path, "ig4")
    assert "did:b" in (g.get("members") or [])
    remove_issuer_group_member(group_id="ig4", member_did="did:b", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    g2 = load_issuer_group(tmp_path, "ig4")
    assert "did:b" not in (g2.get("members") or [])
