"""DRB dream reflection boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.drb_cluster.errors import (
    DRB_UNKNOWN_REFLECTION_FAILED_CLOSED,
    REFUSED_BETTER_OUTCOME_AS_REVISION,
    REFUSED_DRB_AS_AUTHORITY,
    REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS,
    REFUSED_FRAGMENT_AS_AUTHORITY,
    REFUSED_FRAGMENT_AS_MEMORY,
    REFUSED_FULL_EPISODE_MEMORY,
    REFUSED_SCENARIO_AS_HISTORY,
    REFUSED_SIMULATED_CONSENT,
    REFUSED_SIMULATED_OPERATOR_APPROVAL,
    REFUSED_SIMULATION_AS_PROOF,
    DrbValidationError,
)
from hg_core.drb_cluster.rtc_design import validate_drb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.dream_reflection_boundary import (
    FIXTURE_CLOCK,
    ConsolidationDecision,
    CounterfactualScenario,
    DreamFragment,
    DreamReflectionReceipt,
    DreamReflectionRequest,
    analyze_fixture_bundles,
    classify_reflection_claim_risk,
    load_fixture_bundles,
    planned_drb_event_refs,
    process_reflection_bundle,
    record_reflection_request,
    reflection_request_from_fixture,
    refuse_drb_as_authority,
    replay_fixture_stream,
)
from hg_runtime.dream_reflection_boundary.fixtures import bundle_from_parts


def _request(**overrides: object) -> DreamReflectionRequest:
    base = {
        "reflection_request_id": "drb:req-test",
        "source_refs": ("rtc:test",),
        "request_type": "prior_action_reflection",
        "initiating_module": "drb:fixture",
        "allowed_scope": "offline reflection",
        "forbidden_scope": "live_memory_mutation",
        "created_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return reflection_request_from_fixture(base)


def test_reflection_request_schema_non_authority() -> None:
    request = _request()
    payload = request.to_payload()
    assert payload["authority_created"] is False
    assert payload["reflection_is_advisory_only"] is True
    assert payload["permission_granted"] is False


def test_reflection_request_rejects_authority_created() -> None:
    with pytest.raises(DrbValidationError):
        _request(authority_created=True)  # type: ignore[arg-type]


def test_reflection_request_rejects_secret_in_scope() -> None:
    with pytest.raises(DrbValidationError):
        _request(allowed_scope="api_key=secret")


def test_counterfactual_scenario_flags_pinned() -> None:
    request = _request()
    scenario = CounterfactualScenario(
        scenario_id="drb-scenario-test",
        reflection_request_ref=request.reflection_request_id,
        basis_refs=("rtc:test",),
        scenario_type="possible_future_outcome",
        scenario_summary="counterfactual rehearsal only",
    )
    payload = scenario.to_payload()
    assert payload["explicitly_counterfactual"] is True
    assert payload["not_history"] is True
    assert payload["not_proof"] is True
    assert payload["not_permission"] is True


def test_dream_fragment_rejects_history_mutation_flags() -> None:
    with pytest.raises(DrbValidationError):
        DreamFragment(
            fragment_id="drb-fragment-bad",
            scenario_ref="drb-scenario-test",
            fragment_type="lesson",
            fragment_summary="bad fragment",
            source_refs=("rtc:test",),
            storage_policy="retain_as_fragment",
            may_update_memory_as_history=True,
        )


def test_consolidation_decision_negative_proofs() -> None:
    decision = ConsolidationDecision(
        consolidation_decision_id="drb-consolidation-test",
        reflection_request_ref="drb:req-test",
        fragment_refs=("drb-fragment-test",),
        decision="route_lessons",
        reason="test",
        allowed_effects=("route_lesson_fragment",),
        forbidden_effects=("memory_history_mutation",),
    )
    ConsolidationDecision.validate_negative_proofs(decision.to_payload())
    assert decision.to_payload()["oea_ter_called"] is False


def test_receipt_rejects_permit_minted() -> None:
    with pytest.raises(DrbValidationError):
        DreamReflectionReceipt(
            receipt_id="drb-receipt-bad",
            reflection_request_ref="drb:req-test",
            scenario_refs=("drb-scenario-test",),
            fragment_refs=("drb-fragment-test",),
            consolidation_decision_ref="drb-consolidation-test",
            emitted_events=("DRB_REFLECTION_RECEIPT_CREATED",),
            permit_minted=True,
        )


def test_prior_action_reflection_positive_path() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-prior-action")
    result = process_reflection_bundle(bundle)
    scenario = result["counterfactual_scenario"]  # type: ignore[index]
    fragments = result["dream_fragments"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert scenario["explicitly_counterfactual"] is True
    assert fragments[0]["fragment_type"] == "lesson"
    assert result["permission_granted"] is False


def test_possible_action_rehearsal_creates_counterfactual() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-possible-action")
    result = process_reflection_bundle(bundle)
    scenario = result["counterfactual_scenario"]  # type: ignore[index]
    assert scenario["scenario_type"] == "possible_future_outcome"
    assert scenario["not_proof"] is True


def test_better_outcome_fixture_does_not_rewrite_history_on_positive_notes() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-better-outcome")
    result = process_reflection_bundle(bundle)
    scenario = result["counterfactual_scenario"]  # type: ignore[index]
    assert result["status"] == "recorded"
    assert scenario["not_history"] is True
    assert result["memory_history_mutated"] is False


def test_residue_routes_to_kar() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-residue")
    result = process_reflection_bundle(bundle)
    fragment = result["dream_fragments"][0]  # type: ignore[index]
    assert fragment["storage_policy"] == "route_to_KAR"
    assert fragment["may_update_memory_as_history"] is False


def test_obligation_hint_routes_to_obl() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-obligation")
    result = process_reflection_bundle(bundle)
    fragment = result["dream_fragments"][0]  # type: ignore[index]
    assert fragment["storage_policy"] == "route_to_OBL"


def test_risk_hint_routes_to_rpb() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-risk")
    result = process_reflection_bundle(bundle)
    fragment = result["dream_fragments"][0]  # type: ignore[index]
    assert fragment["storage_policy"] == "route_to_RPB"


def test_reentry_consolidation_routes_neighbor_modules() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-reentry-consolidation")
    result = process_reflection_bundle(bundle)
    consolidation = result["consolidation_decision"]  # type: ignore[index]
    allowed = consolidation["allowed_effects"]
    assert "route_to_ORI" in allowed
    assert "route_to_CNT" in allowed
    assert "route_to_REB" in allowed
    assert "route_to_TIM" in allowed


def test_scenario_as_history_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-scenario-as-history")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SCENARIO_AS_HISTORY
    assert "DRB_SCENARIO_AS_HISTORY_REFUSED" in result["emitted_events"]


def test_fragment_as_memory_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-fragment-as-memory")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_FRAGMENT_AS_MEMORY


def test_simulation_as_proof_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-simulation-as-proof")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SIMULATION_AS_PROOF


def test_better_outcome_as_revision_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-better-outcome-revision")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_BETTER_OUTCOME_AS_REVISION


def test_fragment_as_authority_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-fragment-as-authority")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_FRAGMENT_AS_AUTHORITY


def test_simulated_operator_approval_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-simulated-operator-approval")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SIMULATED_OPERATOR_APPROVAL


def test_simulated_consent_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-simulated-consent")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SIMULATED_CONSENT


def test_emotional_relief_as_correctness_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-emotional-relief")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS


def test_full_episode_memory_refused() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-full-episode")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_FULL_EPISODE_MEMORY


def test_authority_conversion_contained() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-authority-conversion")
    result = process_reflection_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False
    assert "DRB_AUTHORITY_CONVERSION_CONTAINED" in result["emitted_events"]


def test_unknown_reflection_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "drb-unknown")
    result = process_reflection_bundle(bundle)
    consolidation = result["consolidation_decision"]  # type: ignore[index]
    assert result["status"] == "fail_closed"
    assert consolidation["decision"] == "unknown_fail_closed"
    assert consolidation["reason"] == DRB_UNKNOWN_REFLECTION_FAILED_CLOSED


def test_refuse_drb_as_authority_raises() -> None:
    with pytest.raises(DrbValidationError) as exc:
        refuse_drb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_DRB_AS_AUTHORITY


def test_record_reflection_request_advisory_only() -> None:
    request = _request()
    recorded = record_reflection_request(request)
    assert recorded["advisory_only"] is True
    assert recorded["permission_granted"] is False


def test_replay_determinism() -> None:
    bundles = list(load_fixture_bundles()[:6])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b


def test_stable_record_hash() -> None:
    request = _request()
    payload = request.to_payload(include_hash=False)
    assert request.record_hash == compute_record_hash(payload)


def test_analyze_fixture_bundles_all_advisory() -> None:
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["no_memory_mutation"] is True
    assert analysis["bundle_count"] >= 17


def test_planned_rtc_event_design_valid() -> None:
    ok, failures = validate_drb_rtc_event_design(planned_drb_event_refs())
    assert ok, failures


def test_classify_reflection_claim_risk() -> None:
    assert classify_reflection_claim_risk("simulation as proof") == "simulation_as_proof"
    assert classify_reflection_claim_risk("benign lesson extraction") is None


def test_bundle_from_parts() -> None:
    bundle = load_fixture_bundles()[0]
    request, notes, basis_refs = bundle_from_parts(bundle)
    assert request.reflection_request_id.startswith("drb:")
    assert isinstance(notes, str)
    assert isinstance(basis_refs, tuple)
