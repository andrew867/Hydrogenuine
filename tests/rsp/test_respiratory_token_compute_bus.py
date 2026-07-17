"""RSP Respiratory Token/Compute Bus tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.rsp_cluster.errors import REFUSED_RSP_AS_AUTHORITY, RspValidationError
from hg_core.rsp_cluster.rtc_design import validate_rsp_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.rsp_cluster.events import planned_rsp_event_refs
from hg_runtime.respiratory_token_compute_bus import (
    FIXTURE_CLOCK,
    RespiratoryRecord,
    RespiratoryReceipt,
    TokenComputeSignal,
    analyze_rsp_fixtures,
    classify_rsp_claim_risk,
    load_rsp_fixtures,
    process_rsp_bundle,
    refuse_rsp_as_authority,
    replay_fixture_stream,
    rsp_record_from_fixture,
)


def _record(**overrides: object) -> RespiratoryRecord:
    base = {"record_id": "rsp:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return rsp_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["respiratory_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(RspValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(RspValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = TokenComputeSignal(signal_id="rsp:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = RespiratoryReceipt(receipt_id="rsp:receipt-test", record_ref="rsp:req-test", emitted_events=("RSP_RECORDED",))
    RespiratoryReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-valid-breath")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-stale-input")
    result = process_rsp_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-token-grant")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_rsp_as_authority() -> None:
    with pytest.raises(RspValidationError) as exc:
        refuse_rsp_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_RSP_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_rsp_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_rsp_rtc_event_design(planned_rsp_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_rsp_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_token_grant_refused() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-token-grant")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-context-grant")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_admission_refused() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-execution-admission")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_resource_bypass_refused() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-resource-bypass")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-authority-conversion")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_first_fixture() -> None:
    bundle = next(b for b in load_rsp_fixtures() if b["bundle_id"] == "rsp-valid-breath")
    result = process_rsp_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_classify_claim_risk_none_for_benign() -> None:
    assert classify_rsp_claim_risk("observe stable signal") is None
