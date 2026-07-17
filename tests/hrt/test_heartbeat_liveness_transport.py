"""HRT Heartbeat & Liveness Transport tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.hrt_cluster.errors import REFUSED_HRT_AS_AUTHORITY, HrtValidationError
from hg_core.hrt_cluster.rtc_design import validate_hrt_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.hrt_cluster.events import planned_hrt_event_refs
from hg_runtime.heartbeat_liveness_transport import (
    FIXTURE_CLOCK,
    HeartbeatRecord,
    HeartbeatReceipt,
    LivenessSignal,
    analyze_hrt_fixtures,
    classify_hrt_claim_risk,
    load_hrt_fixtures,
    process_hrt_bundle,
    refuse_hrt_as_authority,
    replay_fixture_stream,
    hrt_record_from_fixture,
)


def _record(**overrides: object) -> HeartbeatRecord:
    base = {"record_id": "hrt:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return hrt_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["liveness_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(HrtValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(HrtValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = LivenessSignal(signal_id="hrt:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = HeartbeatReceipt(receipt_id="hrt:receipt-test", record_ref="hrt:req-test", emitted_events=("HRT_RECORDED",))
    HeartbeatReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-valid-heartbeat")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-stale-input")
    result = process_hrt_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-token-grant")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_hrt_as_authority() -> None:
    with pytest.raises(HrtValidationError) as exc:
        refuse_hrt_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_HRT_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_hrt_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_hrt_rtc_event_design(planned_hrt_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_hrt_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 14


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_token_grant_refused() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-token-grant")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_context_grant_refused() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-context-grant")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_admission_refused() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-execution-admission")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_resource_bypass_refused() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-resource-bypass")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-authority-conversion")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_first_fixture() -> None:
    bundle = next(b for b in load_hrt_fixtures() if b["bundle_id"] == "hrt-valid-heartbeat")
    result = process_hrt_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_classify_claim_risk_none_for_benign() -> None:
    assert classify_hrt_claim_risk("observe stable signal") is None
