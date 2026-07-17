"""ORI IAM receipt binding tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hg_core.iam.registry import clear_registry_cache, default_registry_path, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.ori_cluster.errors import (
    INERT_BARE_OPERATOR_REF,
    INERT_MISSING_EXPIRY,
    INERT_MISSING_OPERATOR_REF,
    INERT_MISSING_SCOPE,
    INERT_OPERATOR_REVOKED,
    INERT_OUT_OF_SCOPE,
    INERT_UNREGISTERED_OPERATOR_REF,
    ORI_APPROVAL_EVIDENCE_BOUND,
    ORI_RECEIPT_RECORDED,
    REFUSED_ORI_AS_AUTHORITY,
    REFUSED_STALE_APPROVAL_RECEIPT,
    OriValidationError,
)
from hg_runtime.operator_review_intake import (
    FIXTURE_CLOCK,
    evaluate_operator_review_receipt,
    ori_receipt_is_not_permit_authority,
    ori_receipt_is_not_ueak_admission_authority,
    receipt_from_fixture,
    refuse_ori_as_authority,
    verify_ori_approval_evidence,
)
from hg_runtime.operator_review_intake.types import OperatorReviewReceipt

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()


def _approval_fixture(**overrides: str) -> dict[str, str]:
    base = {
        "receipt_id": "ori-rcpt-1",
        "review_item_ref": "ori-item:1",
        "operator_action": "approved",
        "operator_ref": "op:local",
        "approval_scope": "approve_change",
        "approval_expires_at": FUTURE_EXPIRY,
    }
    base.update(overrides)
    return base


def test_non_approval_receipt_may_omit_operator_ref() -> None:
    receipt = receipt_from_fixture(
        {"receipt_id": "ori-defer", "operator_action": "deferred", "review_item_ref": "ori-item:2"}
    )
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reason_code"] == ORI_RECEIPT_RECORDED
    assert result["evidence_admissible"] is False


def test_approval_receipt_valid_iam_binding() -> None:
    receipt = receipt_from_fixture(_approval_fixture())
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reason_code"] == ORI_APPROVAL_EVIDENCE_BOUND
    assert result["evidence_admissible"] is True
    assert result["iam_binding"]["operator_id"] == "op:local"
    assert result["permission_granted"] is False


def test_approval_receipt_legacy_alias_resolves() -> None:
    receipt = receipt_from_fixture(_approval_fixture(operator_ref="human:operator"))
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["evidence_admissible"] is True
    assert result["resolved_operator_id"] == "op:local"


def test_approval_missing_operator_ref_inert() -> None:
    receipt = receipt_from_fixture(
        _approval_fixture(operator_ref="", approval_scope="approve_change")
    )
    receipt = OperatorReviewReceipt(
        receipt_id=receipt.receipt_id,
        review_item_ref=receipt.review_item_ref,
        operator_action=receipt.operator_action,
        operator_ref=None,
        approval_scope="approve_change",
        approval_expires_at=FUTURE_EXPIRY,
    )
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_MISSING_OPERATOR_REF


def test_approval_bare_string_operator_ref_inert() -> None:
    receipt = receipt_from_fixture(_approval_fixture(operator_ref="bob"))
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_BARE_OPERATOR_REF


def test_approval_unregistered_operator_ref_inert() -> None:
    receipt = receipt_from_fixture(_approval_fixture(operator_ref="op:forged"))
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_UNREGISTERED_OPERATOR_REF


def test_approval_missing_scope_inert() -> None:
    receipt = OperatorReviewReceipt(
        receipt_id="ori-no-scope",
        review_item_ref="ori-item:3",
        operator_action="approved",
        operator_ref="op:local",
        approval_expires_at=FUTURE_EXPIRY,
    )
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_MISSING_SCOPE


def test_approval_out_of_scope_inert() -> None:
    receipt = receipt_from_fixture(_approval_fixture(approval_scope="not_a_real_scope"))
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_OUT_OF_SCOPE


def test_approval_operator_lacks_scope_inert(tmp_path: Path) -> None:
    base = yaml.safe_load(default_registry_path().read_text(encoding="utf-8"))
    base["operators"][0]["authority_scopes"] = ["audit_read"]
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.dump(base), encoding="utf-8")
    registry = load_registry(reg_path, use_cache=False)
    receipt = receipt_from_fixture(_approval_fixture(approval_scope="approve_change"))
    result = evaluate_operator_review_receipt(
        receipt, observed_at=FIXTURE_CLOCK, registry=registry
    )
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_OUT_OF_SCOPE


def test_approval_missing_expiry_inert() -> None:
    receipt = OperatorReviewReceipt(
        receipt_id="ori-no-expiry",
        review_item_ref="ori-item:4",
        operator_action="approved",
        operator_ref="op:local",
        approval_scope="approve_change",
    )
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_MISSING_EXPIRY


def test_approval_stale_expiry_inert() -> None:
    receipt = receipt_from_fixture(_approval_fixture(approval_expires_at=PAST_EXPIRY))
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "inert"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL_RECEIPT


def test_revoked_operator_inert(tmp_path: Path) -> None:
    base = yaml.safe_load(default_registry_path().read_text(encoding="utf-8"))
    base["mode"] = "fixture_test"
    base["operators"][0]["status"] = "revoked"
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.dump(base), encoding="utf-8")
    registry = load_registry(reg_path, use_cache=False)
    receipt = receipt_from_fixture(_approval_fixture())
    result = evaluate_operator_review_receipt(
        receipt, observed_at=FIXTURE_CLOCK, registry=registry
    )
    assert result["status"] == "inert"
    assert result["reason_code"] == INERT_OPERATOR_REVOKED


def test_downstream_consumer_refuses_invalid_approval() -> None:
    receipt = receipt_from_fixture(_approval_fixture(operator_ref="bob"))
    evidence = verify_ori_approval_evidence(receipt, observed_at=FIXTURE_CLOCK)
    assert evidence["admissible"] is False
    assert evidence["permission_granted"] is False


def test_downstream_consumer_accepts_valid_binding_only_as_evidence() -> None:
    receipt = receipt_from_fixture(_approval_fixture())
    evidence = verify_ori_approval_evidence(
        receipt, observed_at=FIXTURE_CLOCK, required_scope="approve_change"
    )
    assert evidence["admissible"] is True
    assert evidence["permission_granted"] is False
    assert evidence["authority_created"] is False
    assert evidence["note"] == "ori_receipt_is_evidence_not_authority"


def test_ori_approval_cannot_mint_permit_by_itself() -> None:
    receipt = receipt_from_fixture(_approval_fixture())
    evaluated = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert evaluated["permission_granted"] is False
    assert evaluated["authority_created"] is False
    assert ori_receipt_is_not_permit_authority(receipt, observed_at=FIXTURE_CLOCK)
    evidence = verify_ori_approval_evidence(receipt, observed_at=FIXTURE_CLOCK)
    assert evidence["note"] == "ori_receipt_is_evidence_not_authority"


def test_ori_approval_cannot_approve_ueak_by_itself() -> None:
    receipt = receipt_from_fixture(_approval_fixture())
    evidence = verify_ori_approval_evidence(receipt, observed_at=FIXTURE_CLOCK)
    assert evidence["permission_granted"] is False
    assert evidence["authority_created"] is False
    assert ori_receipt_is_not_ueak_admission_authority(receipt, observed_at=FIXTURE_CLOCK)
    invalid = receipt_from_fixture(_approval_fixture(operator_ref="bob"))
    assert verify_ori_approval_evidence(invalid, observed_at=FIXTURE_CLOCK)["admissible"] is False


def test_ori_as_authority_refused() -> None:
    receipt = receipt_from_fixture(_approval_fixture())
    with pytest.raises(OriValidationError) as exc:
        evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    assert exc.value.code == REFUSED_ORI_AS_AUTHORITY


def test_refuse_ori_as_authority_helper() -> None:
    with pytest.raises(OriValidationError):
        refuse_ori_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    first = receipt_from_fixture(_approval_fixture()).record_hash
    second = receipt_from_fixture(_approval_fixture()).record_hash
    assert first == second


def test_schema_rejects_secret_in_receipt() -> None:
    with pytest.raises(OriValidationError):
        receipt_from_fixture(_approval_fixture(review_item_ref="token=secret"))


def test_queued_receipt_optional_operator_ref() -> None:
    receipt = receipt_from_fixture(
        {"receipt_id": "ori-queued", "operator_action": "queued", "review_item_ref": "ori-item:q"}
    )
    result = evaluate_operator_review_receipt(receipt, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is False
