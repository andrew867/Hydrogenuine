"""Mission cases 17-22: operator decision receipts + chain."""
from __future__ import annotations

import dataclasses

import pytest

from hg_operator_auth.identity import OperatorIdentity, OperatorIdentityError, \
    validate_operator_identity
from hg_operator_auth.receipts import (
    OperatorDecisionReceipt, OperatorReceiptError, demo_local_identity,
    validate_operator_decision_receipt, verify_receipt_chain,
)

KC = dict(provider="keycloak", issuer="http://localhost:8180/realms/hg",
          subject="3f2b8c1e-1111-4222-8333-444455556666",
          display_name="Demo Operator", email="demo-operator@example.local",
          roles=("hg.operator", "hg.approver"),
          session_id_hash="sha256:" + "b" * 64,
          auth_time="2026-07-03T20:59:00Z", assurance_level="password",
          step_up_required=False, step_up_satisfied=False,
          production_operator_auth=True, demo_local_signing=False)


def _receipt(identity, *, prev=None, decision="approve", action_class="promotion",
             breakglass_reason=""):
    return OperatorDecisionReceipt(
        receipt_id="op-dec-0001", decided_at="2026-07-03T21:00:00Z",
        decision=decision, action_class=action_class, risk_category="medium",
        target_ref="claim-001", reason="looks correct",
        operator_identity=identity,
        step_up_required=identity.step_up_required,
        step_up_satisfied=identity.step_up_satisfied,
        breakglass_reason=breakglass_reason, previous_receipt_hash=prev)


def test_keycloak_backed_receipt_validates():
    receipt = _receipt(OperatorIdentity(**KC))
    validate_operator_decision_receipt(receipt)
    payload = receipt.to_payload()
    assert payload["operator_identity"]["production_operator_auth"] is True
    assert payload["operator_identity"]["subject"] == KC["subject"]


def test_demo_local_cannot_claim_production_auth():
    demo = demo_local_identity(operator_id="demo-op-1")
    assert demo.production_operator_auth is False
    validate_operator_identity(demo)  # valid as demo
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(dataclasses.replace(
            demo, production_operator_auth=True))
    assert err.value.code == "demo_local_cannot_claim_production_auth"


def test_production_auth_missing_subject_fails():
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(OperatorIdentity(**{**KC, "subject": ""}))
    assert err.value.code == "production_auth_missing_subject"
    with pytest.raises(OperatorIdentityError):
        validate_operator_identity(OperatorIdentity(**{**KC, "subject": "placeholder"}))


def test_production_auth_missing_issuer_fails():
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(OperatorIdentity(**{**KC, "issuer": " "}))
    assert err.value.code == "production_auth_missing_issuer"


def test_step_up_satisfied_without_evidence_fails():
    bad = OperatorIdentity(**{**KC, "step_up_required": True,
                              "step_up_satisfied": True})
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(bad)
    assert err.value.code == "step_up_satisfied_without_evidence"


def test_raw_token_in_receipt_fails():
    fake_jwt = "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3QifQ.eyJzdWIiOiJ4In0.sig"
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(OperatorIdentity(**{**KC, "display_name": fake_jwt}))
    assert err.value.code == "raw_token_in_identity"
    receipt = _receipt(OperatorIdentity(**KC))
    tampered = dataclasses.replace(receipt, reason=fake_jwt)
    with pytest.raises(OperatorReceiptError) as err2:
        validate_operator_decision_receipt(tampered)
    assert err2.value.code == "raw_token_in_receipt"


def test_session_id_must_be_hashed():
    with pytest.raises(OperatorIdentityError) as err:
        validate_operator_identity(OperatorIdentity(
            **{**KC, "session_id_hash": "raw-session-id-123"}))
    assert err.value.code == "session_id_not_hashed"


def test_receipt_chain_validates_and_breaks_on_tamper():
    r1 = _receipt(OperatorIdentity(**KC))
    r2 = _receipt(demo_local_identity(operator_id="demo-op-1"),
                  prev=r1.receipt_hash, decision="deny")
    chain = [r1.to_payload(), r2.to_payload()]
    assert verify_receipt_chain(chain)["ok"]
    chain[0]["reason"] = "tampered"  # stale hash
    verdict = verify_receipt_chain(chain)
    assert not verdict["ok"] and "hash_mismatch_at_0" in verdict["failures"]
