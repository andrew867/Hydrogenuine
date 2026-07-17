"""OEF Organ Edge Filter tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.oef_cluster.errors import REFUSED_OEF_AS_AUTHORITY, OEFValidationError
from hg_core.oef_cluster.rtc_design import validate_oef_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.oef_cluster.events import planned_oef_event_refs
from hg_runtime.organ_edge_filter import (
    FIXTURE_CLOCK,
    EdgeFilterRequest,
    EdgeFilterReceipt,
    EdgeFilterSignal,
    analyze_oef_fixtures,
    classify_oef_claim_risk,
    load_oef_fixtures,
    process_oef_bundle,
    refuse_oef_as_authority,
    replay_fixture_stream,
    oef_record_from_fixture,
)


def _record(**overrides: object) -> EdgeFilterRequest:
    base = {"record_id": "oef:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return oef_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["edge_filter_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(OEFValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(OEFValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = EdgeFilterSignal(signal_id="oef:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = EdgeFilterReceipt(receipt_id="oef:receipt-test", record_ref="oef:req-test", emitted_events=("OEF_RECORDED",))
    EdgeFilterReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False
    assert receipt.to_payload()["spawn_executed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-valid-ingress")
    result = process_oef_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-stale-input")
    result = process_oef_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_refuse_oef_as_authority() -> None:
    with pytest.raises(OEFValidationError) as exc:
        refuse_oef_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_OEF_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_oef_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_oef_rtc_event_design(planned_oef_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_oef_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_filter_as_permission_refused() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-filter-as-permission")
    result = process_oef_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_missing_tep_refused() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-missing-tep")
    result = process_oef_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_rate_exceeded_refused() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-rate-exceeded")
    result = process_oef_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_positive_valid_ingress() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-valid-ingress")
    result = process_oef_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_egress_filtered() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-egress-filtered")
    result = process_oef_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_quarantine_routed() -> None:
    bundle = next(b for b in load_oef_fixtures() if b["bundle_id"] == "oef-quarantine-routed")
    result = process_oef_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
