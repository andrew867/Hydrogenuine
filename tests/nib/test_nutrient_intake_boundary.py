"""NIB Nutrient Intake Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.nib_cluster.errors import REFUSED_NIB_AS_AUTHORITY, REFUSED_STALE_INPUT, NibValidationError
from hg_core.nib_cluster.rtc_design import validate_nib_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.nib_cluster.events import planned_nib_event_refs
from hg_runtime.nutrient_intake_boundary import (
    FIXTURE_CLOCK,
    IntakeRequest,
    IntakeReceipt,
    IntakeSignal,
    analyze_nib_fixtures,
    classify_nib_claim_risk,
    load_nib_fixtures,
    process_nib_bundle,
    refuse_nib_as_authority,
    replay_fixture_stream,
    nib_record_from_fixture,
)


def _record(**overrides: object) -> IntakeRequest:
    base = {"record_id": "nib:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return nib_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["intake_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(NibValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(NibValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = IntakeSignal(signal_id="nib:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = IntakeReceipt(receipt_id="nib:receipt-test", record_ref="nib:req-test", emitted_events=("NIB_RECORDED",))
    IntakeReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-valid-intake")
    result = process_nib_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-stale-input")
    result = process_nib_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-intake-as-truth")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_nib_as_authority() -> None:
    with pytest.raises(NibValidationError) as exc:
        refuse_nib_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_NIB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_nib_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_nib_rtc_event_design(planned_nib_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_nib_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_intake_as_truth_refused() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-intake-as-truth")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_memory_write_refused() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-memory-write")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_tool_install_refused() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-tool-install")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_budget_grant_refused() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-budget-grant")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-authority-conversion")
    result = process_nib_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_nib_valid_intake() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-valid-intake")
    result = process_nib_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_nib_source_classified() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-source-classified")
    result = process_nib_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_nib_quarantine() -> None:
    bundle = next(b for b in load_nib_fixtures() if b["bundle_id"] == "nib-quarantine")
    result = process_nib_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


