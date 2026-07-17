"""WDB Waste Disposal Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.wdb_cluster.errors import REFUSED_WDB_AS_AUTHORITY, REFUSED_STALE_INPUT, WdbValidationError
from hg_core.wdb_cluster.rtc_design import validate_wdb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.wdb_cluster.events import planned_wdb_event_refs
from hg_runtime.waste_disposal_boundary import (
    FIXTURE_CLOCK,
    WasteCandidate,
    WasteReceipt,
    WasteSignal,
    analyze_wdb_fixtures,
    classify_wdb_claim_risk,
    load_wdb_fixtures,
    process_wdb_bundle,
    refuse_wdb_as_authority,
    replay_fixture_stream,
    wdb_record_from_fixture,
)


def _record(**overrides: object) -> WasteCandidate:
    base = {"record_id": "wdb:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return wdb_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["waste_disposal_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(WdbValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(WdbValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = WasteSignal(signal_id="wdb:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = WasteReceipt(receipt_id="wdb:receipt-test", record_ref="wdb:req-test", emitted_events=("WDB_RECORDED",))
    WasteReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-expired-temp")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-retention-protected")
    result = process_wdb_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-waste-as-deletion")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_wdb_as_authority() -> None:
    with pytest.raises(WdbValidationError) as exc:
        refuse_wdb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_WDB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_wdb_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_wdb_rtc_event_design(planned_wdb_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_wdb_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_waste_as_deletion_refused() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-waste-as-deletion")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_memory_deletion_refused() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-memory-deletion")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_audit_erasure_refused() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-audit-erasure")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_proof_deletion_refused() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-proof-deletion")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-authority-conversion")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_wdb_expired_temp() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-expired-temp")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_wdb_stale_claim() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-stale-claim")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_wdb_tombstone_proposal() -> None:
    bundle = next(b for b in load_wdb_fixtures() if b["bundle_id"] == "wdb-tombstone-proposal")
    result = process_wdb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


