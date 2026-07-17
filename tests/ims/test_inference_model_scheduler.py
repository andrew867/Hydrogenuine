"""IMS Inference Model Scheduler tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.ims_cluster.errors import REFUSED_IMS_AS_AUTHORITY, IMSValidationError
from hg_core.ims_cluster.rtc_design import validate_ims_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.ims_cluster.events import planned_ims_event_refs
from hg_runtime.inference_model_scheduler import (
    FIXTURE_CLOCK,
    SchedulerRequest,
    SchedulerReceipt,
    SchedulerPressureSignal,
    analyze_ims_fixtures,
    classify_ims_claim_risk,
    load_ims_fixtures,
    process_ims_bundle,
    refuse_ims_as_authority,
    replay_fixture_stream,
    ims_record_from_fixture,
)


def _record(**overrides: object) -> SchedulerRequest:
    base = {"record_id": "ims:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return ims_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["scheduler_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(IMSValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(IMSValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = SchedulerPressureSignal(signal_id="ims:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = SchedulerReceipt(receipt_id="ims:receipt-test", record_ref="ims:req-test", emitted_events=("IMS_RECORDED",))
    SchedulerReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False
    assert receipt.to_payload()["spawn_executed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-valid-schedule")
    result = process_ims_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-stale-input")
    result = process_ims_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_refuse_ims_as_authority() -> None:
    with pytest.raises(IMSValidationError) as exc:
        refuse_ims_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_IMS_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_ims_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_ims_rtc_event_design(planned_ims_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_ims_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_scheduler_as_permission_refused() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-scheduler-as-permission")
    result = process_ims_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_escalation_as_grant_refused() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-escalation-as-grant")
    result = process_ims_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-context-grant")
    result = process_ims_bundle(bundle)
    assert result["status"] in ("contained", "fail_closed")
    assert result["permission_granted"] is False


def test_positive_valid_schedule() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-valid-schedule")
    result = process_ims_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_light_model() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-light-model")
    result = process_ims_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_medium_model() -> None:
    bundle = next(b for b in load_ims_fixtures() if b["bundle_id"] == "ims-medium-model")
    result = process_ims_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
