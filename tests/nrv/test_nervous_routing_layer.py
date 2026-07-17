"""NRV Nervous Routing Layer tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.nrv_cluster.errors import REFUSED_NRV_AS_AUTHORITY, NRVValidationError
from hg_core.nrv_cluster.rtc_design import validate_nrv_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.nrv_cluster.events import planned_nrv_event_refs
from hg_runtime.nervous_routing_layer import (
    FIXTURE_CLOCK,
    RoutingRequest,
    RoutingReceipt,
    RoutingPressureSignal,
    analyze_nrv_fixtures,
    classify_nrv_claim_risk,
    load_nrv_fixtures,
    process_nrv_bundle,
    refuse_nrv_as_authority,
    replay_fixture_stream,
    nrv_record_from_fixture,
)


def _record(**overrides: object) -> RoutingRequest:
    base = {"record_id": "nrv:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return nrv_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["routing_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(NRVValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(NRVValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = RoutingPressureSignal(signal_id="nrv:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = RoutingReceipt(receipt_id="nrv:receipt-test", record_ref="nrv:req-test", emitted_events=("NRV_RECORDED",))
    RoutingReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False
    assert receipt.to_payload()["spawn_executed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-valid-route")
    result = process_nrv_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-stale-input")
    result = process_nrv_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_refuse_nrv_as_authority() -> None:
    with pytest.raises(NRVValidationError) as exc:
        refuse_nrv_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_NRV_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_nrv_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_nrv_rtc_event_design(planned_nrv_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_nrv_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_spawn_as_action_refused() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-spawn-as-action")
    result = process_nrv_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_kill_as_action_refused() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-kill-as-action")
    result = process_nrv_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_panic_as_permission_refused() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-panic-as-permission")
    result = process_nrv_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_positive_valid_route() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-valid-route")
    result = process_nrv_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_panic_proposal() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-panic-proposal")
    result = process_nrv_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_degraded_proposal() -> None:
    bundle = next(b for b in load_nrv_fixtures() if b["bundle_id"] == "nrv-degraded-proposal")
    result = process_nrv_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
