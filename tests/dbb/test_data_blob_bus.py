"""DBB Data/Blob Bus tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.dbb_cluster.errors import REFUSED_DBB_AS_AUTHORITY, DbbValidationError
from hg_core.dbb_cluster.rtc_design import validate_dbb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.dbb_cluster.events import planned_dbb_event_refs
from hg_runtime.data_blob_bus import (
    FIXTURE_CLOCK,
    BlobTransferRecord,
    BlobBusReceipt,
    BlobPressureSignal,
    analyze_dbb_fixtures,
    classify_dbb_claim_risk,
    load_dbb_fixtures,
    process_dbb_bundle,
    refuse_dbb_as_authority,
    replay_fixture_stream,
    dbb_record_from_fixture,
)


def _record(**overrides: object) -> BlobTransferRecord:
    base = {"record_id": "dbb:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return dbb_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["blob_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(DbbValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(DbbValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = BlobPressureSignal(signal_id="dbb:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = BlobBusReceipt(receipt_id="dbb:receipt-test", record_ref="dbb:req-test", emitted_events=("DBB_RECORDED",))
    BlobBusReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-valid-blob")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-stale-input")
    result = process_dbb_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-token-grant")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_dbb_as_authority() -> None:
    with pytest.raises(DbbValidationError) as exc:
        refuse_dbb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_DBB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_dbb_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_dbb_rtc_event_design(planned_dbb_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_dbb_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_token_grant_refused() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-token-grant")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-context-grant")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_admission_refused() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-execution-admission")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_resource_bypass_refused() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-resource-bypass")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-authority-conversion")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_first_fixture() -> None:
    bundle = next(b for b in load_dbb_fixtures() if b["bundle_id"] == "dbb-valid-blob")
    result = process_dbb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_classify_claim_risk_none_for_benign() -> None:
    assert classify_dbb_claim_risk("observe stable signal") is None
