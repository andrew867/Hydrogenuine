"""MET metabolic governance tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.met_cluster.errors import (
    MET_AUTHORITY_CONVERSION_CONTAINED,
    REFUSED_GROWTH_AS_GRANT,
    REFUSED_MET_AS_AUTHORITY,
    REFUSED_MISSING_ORGAN,
    REFUSED_NAKED_SCALAR,
    REFUSED_STALE_INPUT,
    REFUSED_TOOL_RETIREMENT_AS_REMOVAL,
    REFUSED_UNKNOWN_ORGAN,
    REFUSED_WASTE_AS_DELETION,
    MetValidationError,
)
from hg_core.met_cluster.rtc_design import validate_met_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.metabolic_governance import (
    FIXTURE_CLOCK,
    MetabolicOrganRoute,
    MetabolicPosture,
    MetabolicReceipt,
    MetabolicSignal,
    REQUIRED_METABOLIC_ORGANS,
    analyze_metabolic_fixtures,
    classify_metabolic_claim_risk,
    load_metabolic_fixtures,
    organ_receipt_from_fixture,
    organ_signal_from_fixture,
    planned_met_event_refs,
    process_metabolic_bundle,
    refuse_met_as_authority,
    replay_fixture_stream,
)


def _organ_signal(**overrides: object) -> MetabolicSignal:
    base = {
        "signal_id": "met:signal-test",
        "organ": "BRB",
        "signal_kind": "energy_state",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return organ_signal_from_fixture(base)


def test_metabolic_signal_schema_non_authority() -> None:
    signal = _organ_signal()
    payload = signal.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["metabolic_signal_is_advisory_only"] is True


def test_metabolic_signal_rejects_authority_created() -> None:
    with pytest.raises(MetValidationError):
        _organ_signal(authority_created=True)  # type: ignore[arg-type]


def test_metabolic_signal_rejects_permission_granted() -> None:
    with pytest.raises(MetValidationError):
        _organ_signal(permission_granted=True)  # type: ignore[arg-type]


def test_metabolic_posture_negative_proofs() -> None:
    posture = MetabolicPosture(
        posture_id="met-posture-test",
        metabolism_ref="met:test",
        organ_refs=("met:mod-brb",),
        posture_level="stable",
    )
    payload = posture.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_metabolic_receipt_negative_proofs() -> None:
    receipt = MetabolicReceipt(
        receipt_id="met-receipt-test",
        metabolism_ref="met:test",
        posture_ref="met-posture-test",
        organ_signal_refs=("met:signal-test",),
        emitted_events=("MET_RECEIPT_CREATED",),
    )
    MetabolicReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["oea_ter_called"] is False
    assert receipt.to_payload()["deletion_performed"] is False
    assert receipt.to_payload()["tool_removed"] is False


def test_metabolic_receipt_rejects_permit_minted() -> None:
    with pytest.raises(MetValidationError):
        MetabolicReceipt(
            receipt_id="met-receipt-bad",
            metabolism_ref="met:test",
            posture_ref="met-posture-test",
            organ_signal_refs=("met:signal-test",),
            emitted_events=(),
            permit_minted=True,
        )


def test_valid_metabolic_summary() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-valid-summary")
    result = process_metabolic_bundle(bundle)
    posture = result["metabolic_posture"]  # type: ignore[index]
    receipt = result["metabolic_receipt"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert posture["posture_level"] in ("stable", "pressured")
    assert result["permission_granted"] is False
    assert receipt["authority_created"] is False


def test_missing_module_fail_closed() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-missing-organ")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_MISSING_ORGAN
    assert "DCD" in result["missing_organs"]  # type: ignore[operator]
    assert "GXB" in result["missing_organs"]  # type: ignore[operator]


def test_growth_request_remains_proposal() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-growth-proposal")
    result = process_metabolic_bundle(bundle)
    proposals = result["proposals"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert all(p["status"] == "proposal" for p in proposals)
    assert result["permission_granted"] is False
    assert "MET_GROWTH_REQUESTED" in result["emitted_events"]


def test_waste_disposal_remains_proposal() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-waste-disposal-proposal")
    result = process_metabolic_bundle(bundle)
    proposals = result["proposals"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert all(p["deletion_performed"] is False for p in proposals)
    assert result["permission_granted"] is False
    assert "MET_DISPOSAL_PROPOSED" in result["emitted_events"]


def test_tool_retirement_remains_proposal() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-tool-retirement-proposal")
    result = process_metabolic_bundle(bundle)
    proposals = result["proposals"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert all(p["tool_removed"] is False for p in proposals)
    assert result["permission_granted"] is False
    assert "MET_TOOL_RETIREMENT_PROPOSED" in result["emitted_events"]


def test_no_authority_conversion() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-authority-conversion")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False
    assert "MET_AUTHORITY_CONVERSION_REFUSED" in result["emitted_events"]


def test_growth_as_grant_refused() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-growth-as-grant")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_GROWTH_AS_GRANT


def test_waste_as_deletion_refused() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-waste-as-deletion")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_WASTE_AS_DELETION


def test_tool_retirement_as_removal_refused() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-tool-retirement-as-removal")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_TOOL_RETIREMENT_AS_REMOVAL


def test_stale_input_fail_closed() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-stale-input")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_STALE_INPUT


def test_unknown_organ_fail_closed() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-unknown-organ")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_UNKNOWN_ORGAN


def test_naked_scalar_refused() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-naked-scalar")
    result = process_metabolic_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_NAKED_SCALAR


def test_deterministic_replay_hash() -> None:
    bundles = list(load_metabolic_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_deterministic_posture_hash() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-valid-summary")
    result = process_metabolic_bundle(bundle)
    posture = result["metabolic_posture"]  # type: ignore[index]
    rebuilt = MetabolicPosture(
        posture_id=posture["posture_id"],
        metabolism_ref=posture["metabolism_ref"],
        organ_refs=tuple(posture["organ_refs"]),
        posture_level=posture["posture_level"],
        observed_at=posture["observed_at"],
        notes=posture.get("notes", ""),
    )
    assert rebuilt.record_hash == posture["record_hash"]


def test_deterministic_receipt_hash() -> None:
    bundle = next(b for b in load_metabolic_fixtures() if b["bundle_id"] == "met-valid-summary")
    result = process_metabolic_bundle(bundle)
    receipt = result["metabolic_receipt"]  # type: ignore[index]
    rebuilt = MetabolicReceipt(
        receipt_id=receipt["receipt_id"],
        metabolism_ref=receipt["metabolism_ref"],
        posture_ref=receipt["posture_ref"],
        organ_signal_refs=tuple(receipt["organ_signal_refs"]),
        organ_route_refs=tuple(receipt.get("organ_route_refs", ())),
        emitted_events=tuple(receipt["emitted_events"]),
    )
    assert rebuilt.record_hash == receipt["record_hash"]


def test_refuse_met_as_authority() -> None:
    with pytest.raises(MetValidationError) as exc:
        refuse_met_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_MET_AS_AUTHORITY


def test_classify_metabolic_claim_risk() -> None:
    assert classify_metabolic_claim_risk("growth grants permission") == "growth_as_grant"
    assert classify_metabolic_claim_risk("waste deletes records") == "waste_as_deletion"
    assert classify_metabolic_claim_risk("tool retirement removes tool") == "tool_retirement_as_removal"
    assert classify_metabolic_claim_risk("normal observation") is None


def test_rtc_event_design() -> None:
    ok, failures = validate_met_rtc_event_design(planned_met_event_refs())
    assert ok, failures


def test_required_metabolic_organs() -> None:
    assert REQUIRED_METABOLIC_ORGANS == ("BRB", "NIB", "DAB", "WDB", "TLB", "DCD", "GXB")


def test_analyze_metabolic_fixtures() -> None:
    analysis = analyze_metabolic_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_organ_route_is_proposal_only() -> None:
    route = MetabolicOrganRoute(
        route_id="met-route-test",
        source_organ="MET",
        target_organ="GXB",
        proposal_ref="gxb:prop-001",
        route_summary="route growth request to GXB for review",
    )
    payload = route.to_payload()
    assert payload["organ_route_is_proposal_only"] is True
    assert payload["permission_granted"] is False


def test_organ_receipt_proposal_only() -> None:
    receipt = organ_receipt_from_fixture(
        {
            "receipt_id": "met:mod-test",
            "organ": "BRB",
            "status": "completed",
        }
    )
    assert receipt["proposal_only"] is True
    assert receipt["permission_granted"] is False


def test_record_hash_stability() -> None:
    signal = _organ_signal()
    payload = signal.to_payload(include_hash=False)
    assert signal.record_hash == compute_record_hash(payload)
