"""BRB Breathing Regulation Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.brb_cluster.errors import REFUSED_BRB_AS_AUTHORITY, REFUSED_STALE_INPUT, BrbValidationError
from hg_core.brb_cluster.rtc_design import validate_brb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.brb_cluster.events import planned_brb_event_refs
from hg_runtime.breathing_regulation_boundary import (
    FIXTURE_CLOCK,
    BreathCycleRecord,
    BreathReceipt,
    BreathPressureSignal,
    analyze_brb_fixtures,
    classify_brb_claim_risk,
    load_brb_fixtures,
    process_brb_bundle,
    refuse_brb_as_authority,
    replay_fixture_stream,
    brb_record_from_fixture,
)


def _record(**overrides: object) -> BreathCycleRecord:
    base = {"record_id": "brb:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return brb_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["breathing_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(BrbValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(BrbValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = BreathPressureSignal(signal_id="brb:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = BreathReceipt(receipt_id="brb:receipt-test", record_ref="brb:req-test", emitted_events=("BRB_RECORDED",))
    BreathReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-valid-cadence")
    result = process_brb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-stale-input")
    result = process_brb_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-token-grant")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_brb_as_authority() -> None:
    with pytest.raises(BrbValidationError) as exc:
        refuse_brb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_BRB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_brb_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_brb_rtc_event_design(planned_brb_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_brb_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_token_grant_refused() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-token-grant")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-context-grant")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_admission_refused() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-execution-admission")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_resource_bypass_refused() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-resource-bypass")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-authority-conversion")
    result = process_brb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_brb_valid_cadence() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-valid-cadence")
    result = process_brb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_brb_token_pressure() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-token-pressure")
    result = process_brb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_brb_compute_pressure() -> None:
    bundle = next(b for b in load_brb_fixtures() if b["bundle_id"] == "brb-compute-pressure")
    result = process_brb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


