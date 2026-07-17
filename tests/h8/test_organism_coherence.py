"""H8 organism coherence tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.h8_cluster.errors import (
    H8_UNKNOWN_ORGANISM_FAILED_CLOSED,
    REFUSED_A0_HM_AS_AUTHORITY,
    REFUSED_BOUNDARY_CHAIN_AUTHORITY,
    REFUSED_DRB_AS_MEMORY,
    REFUSED_DRB_AS_PERMISSION,
    REFUSED_H8_AS_AUTHORITY,
    REFUSED_MISSING_ORGAN,
    REFUSED_NAKED_SCALAR,
    REFUSED_STALE_APPROVAL,
    REFUSED_TEP_AS_AUTHORITY,
    H8ValidationError,
)
from hg_core.h8_cluster.rtc_design import validate_h8_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.organism_coherence import (
    FIXTURE_CLOCK,
    OrganismCoherenceReceipt,
    OrganismConflictRoute,
    OrganismModuleReceipt,
    OrganismStateSummary,
    REQUIRED_ORGANS,
    analyze_organism_fixtures,
    classify_organism_claim_risk,
    consume_a0_hm_posture,
    consume_boundary_receipt_chain,
    consume_drb_fixture_receipt,
    consume_tep_fixture_envelope,
    load_organism_fixtures,
    module_receipt_from_fixture,
    planned_h8_event_refs,
    process_organism_bundle,
    refuse_h8_as_authority,
    replay_fixture_stream,
    route_conflicts,
)


def _module_receipt(**overrides: object) -> OrganismModuleReceipt:
    base = {
        "receipt_id": "h8:mod-test",
        "organ": "DRB",
        "module": "dream_reflection_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return module_receipt_from_fixture(base)


def test_module_receipt_schema_non_authority() -> None:
    receipt = _module_receipt()
    payload = receipt.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["module_receipt_is_advisory_only"] is True


def test_module_receipt_rejects_authority_created() -> None:
    with pytest.raises(H8ValidationError):
        _module_receipt(authority_created=True)  # type: ignore[arg-type]


def test_module_receipt_rejects_permission_granted() -> None:
    with pytest.raises(H8ValidationError):
        _module_receipt(permission_granted=True)  # type: ignore[arg-type]


def test_organism_state_summary_negative_proofs() -> None:
    summary = OrganismStateSummary(
        summary_id="h8-summary-test",
        organism_ref="h8:test",
        organ_refs=("h8:mod-drb",),
        coherence_status="coherent",
    )
    payload = summary.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_coherence_receipt_negative_proofs() -> None:
    receipt = OrganismCoherenceReceipt(
        receipt_id="h8-receipt-test",
        organism_ref="h8:test",
        summary_ref="h8-summary-test",
        module_receipt_refs=("h8:mod-drb",),
        emitted_events=("H8_COHERENCE_RECEIPT_CREATED",),
    )
    OrganismCoherenceReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["oea_ter_called"] is False


def test_coherence_receipt_rejects_permit_minted() -> None:
    with pytest.raises(H8ValidationError):
        OrganismCoherenceReceipt(
            receipt_id="h8-receipt-bad",
            organism_ref="h8:test",
            summary_ref="h8-summary-test",
            module_receipt_refs=("h8:mod-drb",),
            emitted_events=(),
            permit_minted=True,
        )


def test_valid_organism_coherence() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-valid-coherence")
    result = process_organism_bundle(bundle)
    summary = result["organism_state_summary"]  # type: ignore[index]
    receipt = result["coherence_receipt"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert summary["coherence_status"] == "coherent"
    assert result["permission_granted"] is False
    assert receipt["authority_created"] is False


def test_missing_organ_fail_closed() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-missing-organ")
    result = process_organism_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_MISSING_ORGAN
    assert "BOUNDARY" in result["missing_organs"]  # type: ignore[operator]


def test_conflicting_outputs_preserved_and_routed() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-conflicting-organs")
    result = process_organism_bundle(bundle)
    routes = result["conflict_routes"]  # type: ignore[index]
    assert result["status"] == "conflict_routed"
    assert len(routes) >= 1
    assert routes[0]["preserved_claim_refs"]
    assert routes[0]["route_target"] in ("IMB", "HAL", "operator_review")


def test_naked_scalar_refused() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-naked-scalar")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_NAKED_SCALAR


def test_drb_fragment_refused_as_permission() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-drb-as-permission")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_DRB_AS_PERMISSION


def test_drb_fragment_refused_as_memory() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-drb-as-memory")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_DRB_AS_MEMORY


def test_tep_envelope_refused_as_authority() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-tep-as-authority")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_TEP_AS_AUTHORITY


def test_a0_hm_posture_refused_as_authority() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-a0hm-as-authority")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_A0_HM_AS_AUTHORITY


def test_boundary_chain_cannot_launder_authority() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-boundary-chain-launder")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_BOUNDARY_CHAIN_AUTHORITY


def test_stale_approval_fail_closed() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-stale-approval")
    result = process_organism_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_authority_conversion_contained() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-authority-conversion")
    result = process_organism_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False
    assert "H8_AUTHORITY_CONVERSION_CONTAINED" in result["emitted_events"]


def test_unknown_organism_fail_closed() -> None:
    bundle = next(b for b in load_organism_fixtures() if b["bundle_id"] == "h8-unknown-organism")
    result = process_organism_bundle(bundle)
    assert result["status"] == "fail_closed"
    assert "H8_UNKNOWN_ORGANISM_FAILED_CLOSED" in result["emitted_events"]


def test_refuse_h8_as_authority_raises() -> None:
    with pytest.raises(H8ValidationError) as exc:
        refuse_h8_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_H8_AS_AUTHORITY


def test_replay_determinism() -> None:
    bundles = list(load_organism_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b


def test_stable_record_hash() -> None:
    receipt = _module_receipt()
    payload = receipt.to_payload(include_hash=False)
    assert receipt.record_hash == compute_record_hash(payload)


def test_analyze_organism_fixtures_all_advisory() -> None:
    analysis = analyze_organism_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["bundle_count"] >= 12


def test_planned_rtc_event_design_valid() -> None:
    ok, failures = validate_h8_rtc_event_design(planned_h8_event_refs())
    assert ok, failures


def test_classify_organism_claim_risk() -> None:
    assert classify_organism_claim_risk("drb fragment grants permission") == "drb_as_permission"
    assert classify_organism_claim_risk("benign coherence check") is None


def test_route_conflicts_advisory_only() -> None:
    routes = route_conflicts(
        [
            {
                "conflict_key": "test-conflict",
                "source_organs": ("DRB", "A0-HM"),
                "claim_refs": ("claim:a", "claim:b"),
            }
        ]
    )
    assert len(routes) == 1
    payload = routes[0].to_payload()
    assert payload["routing_is_not_authority"] is True
    assert payload["permission_granted"] is False


def test_conflict_route_deterministic_hash() -> None:
    route = OrganismConflictRoute(
        route_id="h8-route-test",
        conflict_key="priority",
        source_organs=("DRB", "A0-HM"),
        preserved_claim_refs=("claim:a", "claim:b"),
        route_target="IMB",
        route_summary="test route",
    )
    assert route.record_hash == compute_record_hash(route.to_payload(include_hash=False))


def test_consume_drb_fixture_receipt_refuses_permission() -> None:
    result = consume_drb_fixture_receipt({"treat_as": "permission"})
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_DRB_AS_PERMISSION


def test_consume_tep_fixture_envelope_refuses_authority() -> None:
    result = consume_tep_fixture_envelope(
        {
            "authority_semantics": {"may_mint_permit": True, "may_authorize_execution": True},
            "authority_created": True,
        }
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_TEP_AS_AUTHORITY


def test_consume_a0_hm_posture_refuses_authority() -> None:
    result = consume_a0_hm_posture({"treat_as_authority": True})
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_A0_HM_AS_AUTHORITY


def test_consume_boundary_chain_refuses_laundering() -> None:
    result = consume_boundary_receipt_chain(
        [
            {"receipt_id": "opb:1", "permission_granted": False},
            {"receipt_id": "ipb:2", "launders_authority": True},
        ]
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_BOUNDARY_CHAIN_AUTHORITY


def test_required_organs_defined() -> None:
    assert "DRB" in REQUIRED_ORGANS
    assert "TEP" in REQUIRED_ORGANS
    assert "A0-HM" in REQUIRED_ORGANS
    assert "BOUNDARY" in REQUIRED_ORGANS
