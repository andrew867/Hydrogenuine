"""DAB Digestion Assimilation Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.dab_cluster.errors import REFUSED_DAB_AS_AUTHORITY, REFUSED_STALE_INPUT, DabValidationError
from hg_core.dab_cluster.rtc_design import validate_dab_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.dab_cluster.events import planned_dab_event_refs
from hg_runtime.digestion_assimilation_boundary import (
    FIXTURE_CLOCK,
    DigestionRequest,
    DigestionReceipt,
    DigestionSignal,
    analyze_dab_fixtures,
    classify_dab_claim_risk,
    load_dab_fixtures,
    process_dab_bundle,
    refuse_dab_as_authority,
    replay_fixture_stream,
    dab_record_from_fixture,
)


def _record(**overrides: object) -> DigestionRequest:
    base = {"record_id": "dab:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return dab_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["digestion_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(DabValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(DabValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = DigestionSignal(signal_id="dab:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = DigestionReceipt(receipt_id="dab:receipt-test", record_ref="dab:req-test", emitted_events=("DAB_RECORDED",))
    DigestionReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-valid-digestion")
    result = process_dab_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-stale-input")
    result = process_dab_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-memory-write")
    result = process_dab_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_dab_as_authority() -> None:
    with pytest.raises(DabValidationError) as exc:
        refuse_dab_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_DAB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_dab_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_dab_rtc_event_design(planned_dab_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_dab_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_memory_write_refused() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-memory-write")
    result = process_dab_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_tool_install_refused() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-tool-install")
    result = process_dab_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_execution_authority_refused() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-execution-authority")
    result = process_dab_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-authority-conversion")
    result = process_dab_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_dab_valid_digestion() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-valid-digestion")
    result = process_dab_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_dab_memory_proposal() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-memory-proposal")
    result = process_dab_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_dab_tool_proposal() -> None:
    bundle = next(b for b in load_dab_fixtures() if b["bundle_id"] == "dab-tool-proposal")
    result = process_dab_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


