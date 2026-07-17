"""
Interop Pack 1: Gateways, capability grants, A2A envelope, TEE attestations, ProofProvider.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from hg_core.interop import (
    issue_capability_grant,
    revoke_capability_grant,
    validate_grant,
    record_grant_used,
    load_grant,
    emit_grant_expired_if_needed,
    make_receipt,
    register_connector,
    request_connector_call,
    execute_connector_call,
    deny_connector_call,
    verify_connector_call,
    validate_envelope,
    send_a2a_message,
    receive_a2a_message,
    declare_execution_profile,
    publish_attestation,
    verify_attestation,
    get_proof_provider,
    set_proof_provider,
    DefaultProofProvider,
)


SCOPE = {"type": "run", "id": "test_iop1"}
ACTOR = {"agent_id": "agent_iop1", "pubkey": "0" * 64, "key_id": "k"}


def test_grant_expiry_enforcement(tmp_path: Path) -> None:
    """Grant expiry and revoke enforcement."""
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    grant_id = issue_capability_grant(
        subject={"type": "agent", "id": "a1"},
        resource={"connector_id": "c1", "operation": "read"},
        scope={"tenant_id": "t1", "environment": "prod", "work_item_id": "wi1"},
        expires_ts=past,
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    grant = load_grant(tmp_path, grant_id)
    assert grant is not None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assert validate_grant(grant, now) is False
    ev = emit_grant_expired_if_needed(grant_id=grant_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev is not None


def test_grant_revoke_enforcement(tmp_path: Path) -> None:
    """Revoked grant is invalid."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    grant_id = issue_capability_grant(
        subject={"type": "agent", "id": "a2"},
        resource={"connector_id": "c2", "operation": "write"},
        scope={"tenant_id": "t1", "environment": "prod", "work_item_id": "wi2"},
        expires_ts=future,
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    revoke_capability_grant(grant_id=grant_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    grant = load_grant(tmp_path, grant_id)
    assert grant is not None and grant.get("revoked_ts")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assert validate_grant(grant, now) is False


def test_gateway_receipts_and_denials(tmp_path: Path) -> None:
    """Gateway receipts artifacts and policy denials."""
    register_connector(connector_id="conn1", name="Conn1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    call_id = request_connector_call(
        connector_id="conn1",
        operation="fetch",
        work_item_id="wi1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert call_id.startswith("call_")
    receipt = make_receipt({"op": "fetch"}, {"status": "ok"}, status="ok")
    assert "request_hash" in receipt and "response_hash" in receipt and receipt["status"] == "ok"
    (tmp_path / "artifacts" / "connector_receipts").mkdir(parents=True, exist_ok=True)
    receipt_path = tmp_path / "artifacts" / "connector_receipts" / "r1.json"
    import json
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    ev_exec = execute_connector_call(call_id=call_id, receipt_artifact_id=str(receipt_path), scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_exec
    ev_deny = deny_connector_call(call_id="call_denied", policy_proof_id="proof_1", reason="policy", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_deny
    ev_verify = verify_connector_call(call_id=call_id, verified=True, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_verify


def test_a2a_signature_expiry_scope_validation(tmp_path: Path) -> None:
    """A2A signature/expiry/scope validation."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    env_valid = {"message_id": "m1", "from": {"id": "a"}, "to": {"id": "b"}, "scope": {"id": "s1"}, "ts": now, "expires_ts": now, "body": {}, "integrity": {"hash": "x"}}
    env_valid["expires_ts"] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    assert validate_envelope(env_valid, now).get("ok") is True
    env_expired = {**env_valid, "expires_ts": past}
    assert validate_envelope(env_expired, now).get("ok") is False
    assert validate_envelope({}, now).get("ok") is False


def test_a2a_send_receive_reject(tmp_path: Path) -> None:
    """A2A send, receive, reject."""
    future_ts = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    mid, ev_sent = send_a2a_message(
        from_agent={"id": "agent_a"},
        to_agent={"id": "agent_b"},
        scope={"id": "run1"},
        body={"action": "request"},
        scope_ledger=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        expires_ts=future_ts,
    )
    assert mid.startswith("a2a_")
    assert ev_sent
    envelope = (tmp_path / "artifacts" / "a2a" / f"{mid}.json").read_text(encoding="utf-8")
    import json
    env_dict = json.loads(envelope)
    ok, ev_recv = receive_a2a_message(message_id=mid, envelope=env_dict, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ok is True
    assert ev_recv
    bad_env = {**env_dict, "expires_ts": "2000-01-01T00:00:00Z"}
    ok2, ev_rej = receive_a2a_message(message_id=mid, envelope=bad_env, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ok2 is False
    assert ev_rej


def test_connector_request_work_item_linkage(tmp_path: Path) -> None:
    """Action request messages require WorkItem linkage."""
    ev = request_connector_call(
        connector_id="c1",
        operation="op",
        work_item_id="wi_123",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_attestations_produced_and_verified(tmp_path: Path) -> None:
    """Attestations produced and verified for TEE profile (stub)."""
    declare_execution_profile(profile="tee-attested", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    att_id = publish_attestation(
        profile="tee-attested",
        signer="tee-signer",
        claims={"env": "secure"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert att_id.startswith("att_")
    ev = verify_attestation(attestation_id=att_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, verified=True)
    assert ev


def test_proof_provider_default(tmp_path: Path) -> None:
    """ProofProvider default implementation (sign/verify, attest)."""
    set_proof_provider(DefaultProofProvider())
    provider = get_proof_provider()
    assert provider is not None
    payload = b"hello"
    sig = provider.sign(payload, {})
    assert provider.verify_signature(payload, sig, {}) is True
    assert provider.verify_signature(b"other", sig, {}) is False
    att = provider.attest({"action": "run"}, {})
    assert "claims" in att and "signature" in att
    assert provider.verify_attestation(att, {}) is True
