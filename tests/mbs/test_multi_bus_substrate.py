"""MBS Multi-Bus Substrate tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.mbs_cluster.errors import REFUSED_MBS_AS_AUTHORITY, MBSValidationError
from hg_core.mbs_cluster.rtc_design import validate_mbs_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.mbs_cluster.events import planned_mbs_event_refs
from hg_runtime.multi_bus_substrate import (
    FIXTURE_CLOCK,
    BusMessageRecord,
    BusReceipt,
    BusPressureSignal,
    analyze_mbs_fixtures,
    classify_mbs_claim_risk,
    load_mbs_fixtures,
    process_mbs_bundle,
    refuse_mbs_as_authority,
    replay_fixture_stream,
    mbs_record_from_fixture,
)


def _record(**overrides: object) -> BusMessageRecord:
    base = {"record_id": "mbs:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return mbs_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["bus_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(MBSValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(MBSValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = BusPressureSignal(signal_id="mbs:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = BusReceipt(receipt_id="mbs:receipt-test", record_ref="mbs:req-test", emitted_events=("MBS_RECORDED",))
    BusReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False
    assert receipt.to_payload()["spawn_executed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-valid-proof-lane")
    result = process_mbs_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-stale-input")
    result = process_mbs_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_refuse_mbs_as_authority() -> None:
    with pytest.raises(MBSValidationError) as exc:
        refuse_mbs_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_MBS_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_mbs_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_mbs_rtc_event_design(planned_mbs_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_mbs_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_bus_as_permission_refused() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-bus-as-permission")
    result = process_mbs_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_lane_bypass_refused() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-lane-bypass")
    result = process_mbs_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_saturation_ignore_refused() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-saturation-ignore")
    result = process_mbs_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_positive_valid_proof_lane() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-valid-proof-lane")
    result = process_mbs_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_data_lane() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-data-lane")
    result = process_mbs_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_resource_lane() -> None:
    bundle = next(b for b in load_mbs_fixtures() if b["bundle_id"] == "mbs-resource-lane")
    result = process_mbs_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
