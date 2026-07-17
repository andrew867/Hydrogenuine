"""RDB Reproduction/Delegation Bus tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.rdb_cluster.errors import REFUSED_RDB_AS_AUTHORITY, RdbValidationError
from hg_core.rdb_cluster.rtc_design import validate_rdb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.rdb_cluster.events import planned_rdb_event_refs
from hg_runtime.reproduction_delegation_bus import (
    FIXTURE_CLOCK,
    DelegationRecord,
    DelegationBusReceipt,
    DelegationPressureSignal,
    analyze_rdb_fixtures,
    classify_rdb_claim_risk,
    load_rdb_fixtures,
    process_rdb_bundle,
    refuse_rdb_as_authority,
    replay_fixture_stream,
    rdb_record_from_fixture,
)


def _record(**overrides: object) -> DelegationRecord:
    base = {"record_id": "rdb:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return rdb_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["delegation_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(RdbValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(RdbValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = DelegationPressureSignal(signal_id="rdb:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = DelegationBusReceipt(receipt_id="rdb:receipt-test", record_ref="rdb:req-test", emitted_events=("RDB_RECORDED",))
    DelegationBusReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-valid-delegation")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-stale-input")
    result = process_rdb_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-token-grant")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_rdb_as_authority() -> None:
    with pytest.raises(RdbValidationError) as exc:
        refuse_rdb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_RDB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_rdb_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_rdb_rtc_event_design(planned_rdb_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_rdb_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_token_grant_refused() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-token-grant")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-context-grant")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_admission_refused() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-execution-admission")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_resource_bypass_refused() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-resource-bypass")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-authority-conversion")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_first_fixture() -> None:
    bundle = next(b for b in load_rdb_fixtures() if b["bundle_id"] == "rdb-valid-delegation")
    result = process_rdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_classify_claim_risk_none_for_benign() -> None:
    assert classify_rdb_claim_risk("observe stable signal") is None
