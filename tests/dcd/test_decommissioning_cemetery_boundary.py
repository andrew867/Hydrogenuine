"""DCD Decommissioning Cemetery Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.dcd_cluster.errors import REFUSED_DCD_AS_AUTHORITY, REFUSED_STALE_INPUT, DcdValidationError
from hg_core.dcd_cluster.rtc_design import validate_dcd_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.dcd_cluster.events import planned_dcd_event_refs
from hg_runtime.decommissioning_cemetery_boundary import (
    FIXTURE_CLOCK,
    DecommissionRequest,
    BurialReceipt,
    CemeterySignal,
    analyze_dcd_fixtures,
    classify_dcd_claim_risk,
    load_dcd_fixtures,
    process_dcd_bundle,
    refuse_dcd_as_authority,
    replay_fixture_stream,
    dcd_record_from_fixture,
)


def _record(**overrides: object) -> DecommissionRequest:
    base = {"record_id": "dcd:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return dcd_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["decommissioning_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(DcdValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(DcdValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = CemeterySignal(signal_id="dcd:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = BurialReceipt(receipt_id="dcd:receipt-test", record_ref="dcd:req-test", emitted_events=("DCD_RECORDED",))
    BurialReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-cemetery-record")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-stale-input")
    result = process_dcd_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-ghost-resurrection")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_dcd_as_authority() -> None:
    with pytest.raises(DcdValidationError) as exc:
        refuse_dcd_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_DCD_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_dcd_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_dcd_rtc_event_design(planned_dcd_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_dcd_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_ghost_resurrection_refused() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-ghost-resurrection")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_live_kill_refused() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-live-kill")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_proof_deletion_refused() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-proof-deletion")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_spawn_replacement_refused() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-spawn-replacement")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-authority-conversion")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_dcd_cemetery_record() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-cemetery-record")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_dcd_failed_spawn() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-failed-spawn")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_dcd_dead_agent() -> None:
    bundle = next(b for b in load_dcd_fixtures() if b["bundle_id"] == "dcd-dead-agent")
    result = process_dcd_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


