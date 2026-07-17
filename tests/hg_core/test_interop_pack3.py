"""
Interop Pack 3: Enterprise bridges, external approvals, inbound receipt proofs.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from hg_core.interop import (
    create_approval_request,
    load_approval_request,
    create_summary_artifact,
    publish_bridge_config,
    verify_and_apply_receipt,
    sign_receipt,
    slack_format_request,
    slack_parse_receipt,
)


SCOPE = {"type": "run", "id": "test_iop3"}
ACTOR = {"agent_id": "agent_iop3", "pubkey": "0" * 64, "key_id": "k"}


def test_outbound_request_creates_summary_and_links_work_item(tmp_path: Path) -> None:
    """Outbound requests create summary artifact and link to work item and policy proof."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(
        work_item_id="wi_1",
        summary_text="Approve deployment to prod",
        risk_cost="low",
        budget_status="within",
        workspace_root=tmp_path,
    )
    assert summary_id.startswith("sum_")
    req_id = create_approval_request(
        work_item_id="wi_1",
        policy_proof_id="proof_1",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={"role": "approver"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert req_id.startswith("req_")
    req = load_approval_request(tmp_path, req_id)
    assert req is not None
    assert req["work_item_id"] == "wi_1"
    assert req["policy_proof_id"] == "proof_1"
    assert req["summary_artifact_id"] == summary_id
    # Slack format uses minimal exposure
    slack_msg = slack_format_request(req)
    assert slack_msg["request_id"] == req_id
    assert "work_item_id" in slack_msg


def test_inbound_invalid_signature_rejected(tmp_path: Path) -> None:
    """Invalid signature on receipt is rejected."""
    publish_bridge_config(
        bridge_id="bridge_a",
        hmac_secret="secret_a",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_2", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_2",
        policy_proof_id="p2",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_bad_sig",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "user1"},
        "ts": future,
        "nonce": "n1",
        "signature": "wrong_signature",
        "bridge_id": "bridge_a",
    }
    accepted, _, reason = verify_and_apply_receipt(
        receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path
    )
    assert accepted is False
    assert reason == "invalid_signature"


def test_inbound_expired_receipt_rejected(tmp_path: Path) -> None:
    """Expired receipt is rejected."""
    publish_bridge_config(bridge_id="bridge_b", hmac_secret="secret_b", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_3", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_3",
        policy_proof_id="p3",
        expires_ts=past,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_exp",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "u2"},
        "ts": past,
        "nonce": "n_exp",
        "bridge_id": "bridge_b",
    }
    receipt = sign_receipt(receipt, "bridge_b", tmp_path)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    accepted, _, reason = verify_and_apply_receipt(
        receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, now_ts=now
    )
    assert accepted is False
    assert reason == "expired"


def test_inbound_nonce_replay_rejected(tmp_path: Path) -> None:
    """Nonce/receipt replay is rejected."""
    publish_bridge_config(bridge_id="bridge_c", hmac_secret="secret_c", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_4", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_4",
        policy_proof_id="p4",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_replay",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "u3"},
        "ts": future,
        "nonce": "n_replay",
        "bridge_id": "bridge_c",
    }
    receipt = sign_receipt(receipt, "bridge_c", tmp_path)
    accepted1, _, _ = verify_and_apply_receipt(receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert accepted1 is True
    accepted2, _, reason = verify_and_apply_receipt(receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert accepted2 is False
    assert reason == "replay"


def test_inbound_scope_mismatch_rejected(tmp_path: Path) -> None:
    """Scope mismatch on receipt is rejected."""
    publish_bridge_config(bridge_id="bridge_d", hmac_secret="secret_d", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_5", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_5",
        policy_proof_id="p5",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_scope",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "u4"},
        "ts": future,
        "nonce": "n_scope",
        "bridge_id": "bridge_d",
    }
    receipt = sign_receipt(receipt, "bridge_d", tmp_path)
    wrong_scope = {"type": "run", "id": "other_run"}
    accepted, _, reason = verify_and_apply_receipt(
        receipt=receipt, scope=wrong_scope, actor=ACTOR, workspace_root=tmp_path
    )
    assert accepted is False
    assert reason == "scope_mismatch"


def test_inbound_independence_rule_rejected(tmp_path: Path) -> None:
    """Independence rule violation (disallowed approver) is rejected."""
    publish_bridge_config(bridge_id="bridge_e", hmac_secret="secret_e", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_6", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_6",
        policy_proof_id="p6",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_indep",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "requestor_agent"},
        "ts": future,
        "nonce": "n_indep",
        "bridge_id": "bridge_e",
    }
    receipt = sign_receipt(receipt, "bridge_e", tmp_path)
    accepted, _, reason = verify_and_apply_receipt(
        receipt=receipt,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        disallowed_approver_ids={"requestor_agent"},
    )
    assert accepted is False
    assert reason == "independence_rule"


def test_valid_receipt_produces_approval_granted(tmp_path: Path) -> None:
    """Valid receipt produces APPROVAL_GRANTED with references."""
    publish_bridge_config(bridge_id="bridge_f", hmac_secret="secret_f", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_7", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_7",
        policy_proof_id="p7",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_ok",
        "request_id": req_id,
        "decision": "approve",
        "approver": {"id": "approver_1"},
        "ts": future,
        "nonce": "n_ok",
        "bridge_id": "bridge_f",
    }
    receipt = sign_receipt(receipt, "bridge_f", tmp_path)
    accepted, event_id, reason = verify_and_apply_receipt(
        receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path
    )
    assert accepted is True
    assert reason is None
    assert event_id


def test_valid_receipt_deny_produces_approval_denied(tmp_path: Path) -> None:
    """Valid receipt with decision deny produces APPROVAL_DENIED."""
    publish_bridge_config(bridge_id="bridge_g", hmac_secret="secret_g", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_8", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_8",
        policy_proof_id="p8",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    receipt = {
        "receipt_id": "rec_deny",
        "request_id": req_id,
        "decision": "deny",
        "approver": {"id": "approver_2"},
        "ts": future,
        "nonce": "n_deny",
        "bridge_id": "bridge_g",
    }
    receipt = sign_receipt(receipt, "bridge_g", tmp_path)
    accepted, event_id, reason = verify_and_apply_receipt(
        receipt=receipt, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path
    )
    assert accepted is True
    assert reason is None
    assert event_id


def test_bridge_send_idempotent_no_adapter(tmp_path: Path) -> None:
    """Bridge send without adapter is idempotent (ok, no-op)."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    summary_id = create_summary_artifact(work_item_id="wi_9", summary_text="Approve", workspace_root=tmp_path)
    req_id = create_approval_request(
        work_item_id="wi_9",
        policy_proof_id="p9",
        expires_ts=future,
        summary_artifact_id=summary_id,
        required_claims={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    from hg_core.interop.approval_bridge import send_via_bridge
    ok1, _ = send_via_bridge(request_id=req_id, bridge_id="slack", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ok2, _ = send_via_bridge(request_id=req_id, bridge_id="slack", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ok1 is True
    assert ok2 is True


def test_slack_parse_receipt(tmp_path: Path) -> None:
    """Slack parse_receipt normalizes payload to receipt shape."""
    raw = {
        "request_id": "req_x",
        "receipt_id": "rec_x",
        "user": {"id": "U123", "name": "alice"},
        "actions": [{"value": "approve"}],
        "ts": "123.456",
    }
    rec = slack_parse_receipt(raw)
    assert rec is not None
    assert rec["request_id"] == "req_x"
    assert rec["decision"] == "approve"
    assert rec["approver"]["id"] == "U123"
    assert rec["bridge_id"] == "slack"
