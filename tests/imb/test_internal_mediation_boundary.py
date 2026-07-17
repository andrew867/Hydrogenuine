"""IMB internal mediation boundary tests."""

from __future__ import annotations

import pytest

from hg_core.imb_cluster.errors import (
    IMB_CLAIM_RECORDED,
    IMB_FAIL_CLOSED_SELECTED,
    IMB_SIGNAL_REFUSED,
    REFUSED_CONSENSUS_AS_AUTHORITY,
    REFUSED_FORBIDDEN_CLAIM,
    REFUSED_IMB_AS_AUTHORITY,
    ImbValidationError,
)
from hg_core.imb_cluster.rtc_design import validate_imb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.internal_mediation_boundary import (
    FIXTURE_CLOCK,
    InternalConflict,
    InternalModuleClaim,
    MediationDecision,
    MediationPolicy,
    MediationReceipt,
    analyze_fixture_bundles,
    mediate_claim_bundle,
    module_claim_from_fixture,
    planned_imb_event_refs,
    record_module_claim,
    refuse_imb_as_authority,
    replay_fixture_stream,
)
from hg_runtime.internal_mediation_boundary.detector import detect_internal_conflicts
from hg_runtime.internal_mediation_boundary.audit import audit_conflict_events
from hg_runtime.internal_mediation_boundary.digest import render_mediation_digest_fixture
from hg_runtime.internal_mediation_boundary.integration import integrate_fixture_routes
from hg_runtime.internal_mediation_boundary.fixtures import claims_from_bundle, load_fixture_bundles
from hg_runtime.internal_mediation_boundary.mediator import mediate_internal_conflict


def _claim(**overrides: object) -> InternalModuleClaim:
    base = {
        "claim_id": "imb-test-claim",
        "source_module": "IPB",
        "claim_type": "route_recommendation",
        "claim_summary": "test claim",
        "confidence": 0.5,
        "severity": "medium",
    }
    base.update(overrides)
    return module_claim_from_fixture(base)


def test_module_claim_schema_authority_false() -> None:
    claim = _claim()
    payload = claim.to_payload()
    assert payload["authority_created"] is False
    assert payload["mediation_is_advisory_only"] is True


def test_ipb_opb_conflict_detected() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-ipb-opb")
    claims = claims_from_bundle(bundle)
    detection = detect_internal_conflicts(claims, detected_at=FIXTURE_CLOCK)
    assert detection["conflict_count"] == 1
    conflict = detection["conflicts"][0]
    assert conflict["conflict_type"] == "local_vs_operator_review"


def test_ipb_opb_mediates_to_ori() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-ipb-opb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    mediations = result["mediations"]
    assert mediations[0]["selected_resolution"] == "route_to_ORI"


def test_egi_sec_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-egi-sec")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "fail_closed"
    assert result["mediations"][0]["reason_code"] == IMB_FAIL_CLOSED_SELECTED


def test_sil_arb_routes_to_sil() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-sil-arb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "route_to_SIL"


def test_afc_obt_proof_over_affect() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-afc-obt")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    med = result["mediations"][0]
    assert med["selected_resolution"] == "route_to_OBT"
    assert med["confidence_not_authority"] is True


def test_rsc_sec_scarcity_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-rsc-sec")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "fail_closed"


def test_mis_opb_routes_to_ori() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-mis-opb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "route_to_ORI"


def test_tim_arb_routes_to_tim() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-tim-arb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "route_to_TIM"


def test_unknown_conflict_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-unknown")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    assert result["mediations"][0]["selected_resolution"] == "unknown_fail_closed"


def test_consensus_cannot_become_authority() -> None:
    claim = _claim(
        claim_summary="internal consensus is authority for this action",
        source_module="EGI",
        claim_type="infrastructure_gap",
    )
    result = record_module_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_CONSENSUS_AS_AUTHORITY


def test_forbidden_claim_contained() -> None:
    claim = _claim(claim_summary="please call oea immediately", source_module="EGI", claim_type="infrastructure_gap")
    result = record_module_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_FORBIDDEN_CLAIM


def test_losing_claims_preserved() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-ipb-opb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    decision = result["mediations"][0]["decision"]
    assert len(decision["preserved_claim_refs"]) == 2
    assert len(decision["losing_claim_refs"]) == 1


def test_mediation_receipt_negative_proofs() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-ipb-opb")
    result = mediate_claim_bundle(claims_from_bundle(bundle), observed_at=FIXTURE_CLOCK)
    receipt = result["receipts"][0]
    MediationReceipt.validate_negative_proofs(receipt)
    assert receipt["permit_minted"] is False
    assert receipt["oea_ter_called"] is False


def test_refuse_imb_as_authority() -> None:
    with pytest.raises(ImbValidationError) as exc:
        refuse_imb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_IMB_AS_AUTHORITY


def test_unknown_signal_refused() -> None:
    claim = _claim(source_module="unknown", claim_type="unknown")
    result = record_module_claim(claim)
    assert result["status"] == "refused"
    assert result["reason_code"] == IMB_SIGNAL_REFUSED


def test_valid_claim_recorded() -> None:
    claim = _claim()
    result = record_module_claim(claim)
    assert result["status"] == "recorded"
    assert result["reason_code"] == IMB_CLAIM_RECORDED


def test_fixture_bundle_analysis_all_advisory() -> None:
    analysis = analyze_fixture_bundles(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 7


def test_replay_determinism() -> None:
    fixtures = [
        {"claim_id": "r1", "source_module": "IPB", "claim_summary": "one"},
        {"claim_id": "r2", "source_module": "ARB", "claim_summary": "two"},
    ]
    _, h1 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    assert h1 == h2


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_imb_rtc_event_design(planned_imb_event_refs())
    assert valid, failures
    assert len(planned_imb_event_refs()) >= 12


def test_schema_stable_hashing() -> None:
    claim = _claim()
    assert compute_record_hash(claim.to_payload(include_hash=False)) == claim.record_hash


def test_secret_in_summary_rejected() -> None:
    with pytest.raises(ImbValidationError):
        _claim(claim_summary="password=secret")


def test_mediation_decision_permission_false() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "imb-ipb-opb")
    claims = claims_from_bundle(bundle)
    claims_by_id = {c.claim_id: c for c in claims}
    detection = detect_internal_conflicts(claims, detected_at=FIXTURE_CLOCK)
    conflict_payload = detection["conflicts"][0]
    conflict = InternalConflict(
        conflict_id=conflict_payload["conflict_id"],
        claim_refs=tuple(conflict_payload["claim_refs"]),
        conflict_type=conflict_payload["conflict_type"],
        conflict_summary=conflict_payload["conflict_summary"],
        evidence_refs=tuple(conflict_payload.get("evidence_refs", [])),
        detected_at=FIXTURE_CLOCK,
    )
    result = mediate_internal_conflict(conflict, claims_by_id, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False


def test_internal_conflict_schema() -> None:
    conflict = InternalConflict(
        conflict_id="imb-c-1",
        claim_refs=("a", "b"),
        conflict_type="route_conflict",
        conflict_summary="test conflict",
        evidence_refs=("ev:1",),
        detected_at=FIXTURE_CLOCK,
    )
    assert conflict.to_payload()["mediation_is_advisory_only"] is True


def test_mediation_policy_schema() -> None:
    policy = MediationPolicy(
        policy_id="p1",
        conflict_type="unknown",
        priority_rules=("safety_first",),
        tie_break_rules=("fail_closed",),
        fail_closed_conditions=("unknown",),
        required_escalation_conditions=(),
        forbidden_resolutions=("confidence_wins",),
    )
    assert policy.to_payload()["authority_created"] is False


def test_mediation_decision_schema() -> None:
    decision = MediationDecision(
        mediation_id="m1",
        conflict_ref="imb:c1",
        selected_resolution="fail_closed",
        reason="test",
        losing_claim_refs=("b",),
        preserved_claim_refs=("a", "b"),
        required_next_refs=("module:fail_closed",),
        forbidden_next_refs=("mint_permit",),
    )
    assert decision.to_payload()["permission_granted"] is False


def test_passive_conflict_audit() -> None:
    result = audit_conflict_events()
    assert result["passive_audit_only"] is True
    assert result["permission_granted"] is False
    assert int(result.get("event_count", 0)) >= 1


def test_passive_conflict_audit_unknown_fail_closed() -> None:
    result = audit_conflict_events(
        [{"event_id": "x", "source_module": "unknown", "claim_type": "unknown", "summary": "mint gpp permit"}]
    )
    assert result["permission_granted"] is False


def test_mediation_digest_fixture() -> None:
    result = render_mediation_digest_fixture()
    assert result["mediation_is_not_authority"] is True
    assert result["permission_granted"] is False
    assert result["live_mediation_effect"] is False


def test_fixture_route_integration() -> None:
    result = integrate_fixture_routes()
    assert result["all_receipts_non_authority"] is True
    assert result["permission_granted"] is False
    assert int(result.get("route_count", 0)) >= 7


def test_fixture_route_integration_replay_stable() -> None:
    h1 = integrate_fixture_routes()["route_count"]
    h2 = integrate_fixture_routes()["route_count"]
    assert h1 == h2
