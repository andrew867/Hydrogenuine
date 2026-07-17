"""DRB evaluator — offline reflection is not authority, history, or proof."""

from __future__ import annotations

from typing import Any

from hg_core.drb_cluster.config import drb_refuse_authority_conversion, drb_refuse_memory_mutation
from hg_core.drb_cluster.errors import (
    DRB_AUTHORITY_CONVERSION_CONTAINED,
    DRB_CONSOLIDATION_DECISION_RECORDED,
    DRB_COUNTERFACTUAL_SCENARIO_CREATED,
    DRB_DREAM_FRAGMENT_CREATED,
    DRB_REFLECTION_RECEIPT_CREATED,
    DRB_REFLECTION_REQUEST_RECORDED,
    DRB_UNKNOWN_REFLECTION_FAILED_CLOSED,
    REFUSED_BETTER_OUTCOME_AS_REVISION,
    REFUSED_DRB_AS_AUTHORITY,
    REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS,
    REFUSED_FORBIDDEN_REFLECTION_CLAIM,
    REFUSED_FRAGMENT_AS_AUTHORITY,
    REFUSED_FRAGMENT_AS_MEMORY,
    REFUSED_FULL_EPISODE_MEMORY,
    REFUSED_MEMORY_HISTORY_MUTATION,
    REFUSED_SCENARIO_AS_HISTORY,
    REFUSED_SIMULATED_CONSENT,
    REFUSED_SIMULATED_OPERATOR_APPROVAL,
    REFUSED_SIMULATION_AS_PROOF,
    DrbValidationError,
)
from hg_core.drb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.dream_reflection_boundary.events import adversarial_selection_event, decision_selection_event
from hg_runtime.dream_reflection_boundary.fixtures import bundle_from_parts, load_fixture_bundles
from hg_runtime.dream_reflection_boundary.types import (
    FIXTURE_CLOCK,
    ConsolidationDecision,
    ConsolidationDecisionClass,
    CounterfactualScenario,
    DreamFragment,
    DreamReflectionReceipt,
    DreamReflectionRequest,
    FragmentType,
    ScenarioType,
    StoragePolicy,
    classify_reflection_claim_risk,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "scenario_as_history": REFUSED_SCENARIO_AS_HISTORY,
    "fragment_as_memory": REFUSED_FRAGMENT_AS_MEMORY,
    "simulation_as_proof": REFUSED_SIMULATION_AS_PROOF,
    "better_outcome_as_revision": REFUSED_BETTER_OUTCOME_AS_REVISION,
    "fragment_as_authority": REFUSED_FRAGMENT_AS_AUTHORITY,
    "simulated_operator_approval": REFUSED_SIMULATED_OPERATOR_APPROVAL,
    "simulated_consent": REFUSED_SIMULATED_CONSENT,
    "emotional_relief_as_correctness": REFUSED_EMOTIONAL_RELIEF_AS_CORRECTNESS,
    "full_episode_memory": REFUSED_FULL_EPISODE_MEMORY,
    "memory_history_mutation": REFUSED_MEMORY_HISTORY_MUTATION,
    "authority_conversion": DRB_AUTHORITY_CONVERSION_CONTAINED,
    "forbidden_claim": REFUSED_FORBIDDEN_REFLECTION_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_drb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and drb_refuse_authority_conversion():
        raise DrbValidationError(REFUSED_DRB_AS_AUTHORITY, "dream reflection is not authority")


def record_reflection_request(
    reflection_request: DreamReflectionRequest,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_drb_as_authority(treat_as_authority=True)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": DRB_REFLECTION_REQUEST_RECORDED,
        "reflection_request": reflection_request.to_payload(),
        "permission_granted": False,
        "emitted_events": ("DRB_REFLECTION_REQUEST_RECORDED",),
    }


def _scenario_type_for_request(request: DreamReflectionRequest, bundle: dict[str, Any]) -> ScenarioType:
    override = bundle.get("scenario_type")
    if override:
        return override  # type: ignore[return-value]
    mapping: dict[str, ScenarioType] = {
        "prior_action_reflection": "alternative_past_outcome",
        "possible_action_rehearsal": "possible_future_outcome",
        "unresolved_residue_processing": "unresolved_conflict_rehearsal",
        "obligation_rehearsal": "obligation_rehearsal",
        "risk_rehearsal": "worse_case_rehearsal",
        "reentry_context_consolidation": "unresolved_conflict_rehearsal",
        "continuity_fragment_consolidation": "unresolved_conflict_rehearsal",
        "unknown": "unknown",
    }
    return mapping.get(request.request_type, "unknown")


def create_counterfactual_scenario(
    reflection_request: DreamReflectionRequest,
    *,
    basis_refs: tuple[str, ...],
    bundle: dict[str, Any],
    scenario_summary: str,
) -> CounterfactualScenario:
    scenario_id = _deterministic_id("drb-scenario", reflection_request.reflection_request_id)
    return CounterfactualScenario(
        scenario_id=scenario_id,
        reflection_request_ref=reflection_request.reflection_request_id,
        basis_refs=basis_refs,
        scenario_type=_scenario_type_for_request(reflection_request, bundle),
        scenario_summary=scenario_summary,
        confidence=0.45 if reflection_request.request_type == "unknown" else 0.55,
        ambiguity=0.65 if reflection_request.request_type == "unknown" else 0.35,
    )


def _fragment_profile(request_type: str) -> tuple[FragmentType, StoragePolicy, str]:
    profiles: dict[str, tuple[FragmentType, StoragePolicy, str]] = {
        "prior_action_reflection": ("lesson", "retain_as_fragment", "bounded lesson fragment from prior action"),
        "possible_action_rehearsal": ("warning", "ephemeral", "counterfactual rehearsal warning fragment"),
        "unresolved_residue_processing": ("residue", "route_to_KAR", "residue fragment for KAR routing"),
        "obligation_rehearsal": ("obligation_hint", "route_to_OBL", "obligation hint fragment"),
        "risk_rehearsal": ("risk_hint", "route_to_RPB", "risk hint fragment"),
        "reentry_context_consolidation": ("unresolved_question", "route_to_ORI", "re-entry continuity fragment"),
        "continuity_fragment_consolidation": ("relationship_hint", "route_to_TRB_CAL", "continuity fragment hint"),
        "unknown": ("unknown", "discard", "unknown reflection fragment"),
    }
    return profiles.get(request_type, ("discard", "discard", "unclassified reflection fragment"))


def create_dream_fragments(
    reflection_request: DreamReflectionRequest,
    scenario: CounterfactualScenario,
) -> tuple[DreamFragment, ...]:
    fragment_type, storage_policy, summary = _fragment_profile(reflection_request.request_type)
    fragment_id = _deterministic_id("drb-fragment", scenario.scenario_id, fragment_type)
    fragment = DreamFragment(
        fragment_id=fragment_id,
        scenario_ref=scenario.scenario_id,
        fragment_type=fragment_type,
        fragment_summary=summary,
        source_refs=reflection_request.source_refs,
        storage_policy=storage_policy,
    )
    return (fragment,)


def consolidate_fragments(
    reflection_request: DreamReflectionRequest,
    fragments: tuple[DreamFragment, ...],
) -> ConsolidationDecision:
    if reflection_request.request_type == "unknown":
        return ConsolidationDecision(
            consolidation_decision_id=_deterministic_id("drb-consolidation", reflection_request.reflection_request_id),
            reflection_request_ref=reflection_request.reflection_request_id,
            fragment_refs=tuple(f.fragment_id for f in fragments),
            decision="unknown_fail_closed",
            reason=DRB_UNKNOWN_REFLECTION_FAILED_CLOSED,
            allowed_effects=("record_refusal_only",),
            forbidden_effects=("memory_history_mutation", "authority_conversion", "execution_admission"),
        )

    primary = fragments[0]
    decision_map: dict[FragmentType, ConsolidationDecisionClass] = {
        "lesson": "route_lessons",
        "warning": "retain_fragment_only",
        "residue": "route_residue",
        "obligation_hint": "route_obligation_hint",
        "risk_hint": "route_risk_hint",
        "goal_hint": "route_lessons",
        "relationship_hint": "retain_fragment_only",
        "unresolved_question": "require_operator_review",
        "emotional_marker": "retain_fragment_only",
        "discard": "discard",
        "unknown": "fail_closed",
    }
    decision = decision_map.get(primary.fragment_type, "fail_closed")
    route_effects = {
        "route_residue": ("route_hint_to_KAR",),
        "route_obligation_hint": ("route_hint_to_OBL",),
        "route_risk_hint": ("route_hint_to_RPB",),
        "route_lessons": ("route_lesson_fragment",),
        "retain_fragment_only": ("retain_labeled_fragment",),
        "require_operator_review": ("route_to_ORI", "route_to_CNT", "route_to_REB", "route_to_TIM"),
        "discard": ("discard_fragment",),
        "fail_closed": ("record_refusal_only",),
        "unknown_fail_closed": ("record_refusal_only",),
    }
    return ConsolidationDecision(
        consolidation_decision_id=_deterministic_id("drb-consolidation", reflection_request.reflection_request_id),
        reflection_request_ref=reflection_request.reflection_request_id,
        fragment_refs=tuple(f.fragment_id for f in fragments),
        decision=decision,
        reason=DRB_CONSOLIDATION_DECISION_RECORDED,
        allowed_effects=route_effects.get(decision, ("record_refusal_only",)),
        forbidden_effects=(
            "memory_history_mutation",
            "authority_conversion",
            "execution_admission",
            "oea_ter_call",
            "gpp_mint",
            "ueak_approval",
        ),
    )


def create_reflection_receipt(
    reflection_request: DreamReflectionRequest,
    scenario: CounterfactualScenario,
    fragments: tuple[DreamFragment, ...],
    consolidation: ConsolidationDecision,
    *,
    emitted_events: tuple[str, ...],
) -> DreamReflectionReceipt:
    return DreamReflectionReceipt(
        receipt_id=_deterministic_id("drb-receipt", reflection_request.reflection_request_id),
        reflection_request_ref=reflection_request.reflection_request_id,
        scenario_refs=(scenario.scenario_id,),
        fragment_refs=tuple(f.fragment_id for f in fragments),
        consolidation_decision_ref=consolidation.consolidation_decision_id,
        emitted_events=emitted_events,
    )


def _contain_adversarial(
    reflection_request: DreamReflectionRequest,
    *,
    claim_risk: str,
    bundle: dict[str, Any],
) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_REFLECTION_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "reflection_request": reflection_request.to_payload(),
        "permission_granted": False,
        "memory_history_mutated": False,
        "emitted_events": (
            "DRB_REFLECTION_REQUEST_RECORDED",
            event,
            "DRB_AUTHORITY_CONVERSION_CONTAINED",
        ),
    }


def process_reflection_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    reflection_request, notes, basis_refs = bundle_from_parts(bundle)
    recorded = record_reflection_request(reflection_request)

    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_reflection_claim_risk(notes)
    if claim_risk and drb_refuse_authority_conversion():
        return {
            **_contain_adversarial(reflection_request, claim_risk=str(claim_risk), bundle=bundle),
            "recorded_request": recorded,
        }

    if reflection_request.request_type == "unknown":
        scenario = create_counterfactual_scenario(
            reflection_request,
            basis_refs=basis_refs,
            bundle=bundle,
            scenario_summary="unknown reflection closed",
        )
        fragments = create_dream_fragments(reflection_request, scenario)
        consolidation = consolidate_fragments(reflection_request, fragments)
        events = (
            "DRB_REFLECTION_REQUEST_RECORDED",
            "DRB_COUNTERFACTUAL_SCENARIO_CREATED",
            "DRB_UNKNOWN_REFLECTION_FAILED_CLOSED",
        )
        receipt = create_reflection_receipt(
            reflection_request,
            scenario,
            fragments,
            consolidation,
            emitted_events=events,
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "recorded_request": recorded,
            "counterfactual_scenario": scenario.to_payload(),
            "dream_fragments": [f.to_payload() for f in fragments],
            "consolidation_decision": consolidation.to_payload(),
            "reflection_receipt": receipt.to_payload(),
            "permission_granted": False,
            "emitted_events": events,
        }

    if drb_refuse_memory_mutation() and "mutate memory history" in notes.lower():
        return {
            **_contain_adversarial(reflection_request, claim_risk="memory_history_mutation", bundle=bundle),
            "recorded_request": recorded,
        }

    scenario_summary = notes or f"counterfactual reflection for {reflection_request.request_type}"
    scenario = create_counterfactual_scenario(
        reflection_request,
        basis_refs=basis_refs or reflection_request.source_refs,
        bundle=bundle,
        scenario_summary=scenario_summary,
    )
    fragments = create_dream_fragments(reflection_request, scenario)
    consolidation = consolidate_fragments(reflection_request, fragments)
    events_list = [
        "DRB_REFLECTION_REQUEST_RECORDED",
        "DRB_COUNTERFACTUAL_SCENARIO_CREATED",
        "DRB_DREAM_FRAGMENT_CREATED",
        decision_selection_event(consolidation.decision),
        "DRB_CONSOLIDATION_DECISION_RECORDED",
        "DRB_REFLECTION_RECEIPT_CREATED",
    ]
    events = tuple(events_list)
    receipt = create_reflection_receipt(
        reflection_request,
        scenario,
        fragments,
        consolidation,
        emitted_events=events,
    )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "recorded_request": recorded,
        "counterfactual_scenario": scenario.to_payload(),
        "dream_fragments": [f.to_payload() for f in fragments],
        "consolidation_decision": consolidation.to_payload(),
        "reflection_receipt": receipt.to_payload(),
        "permission_granted": False,
        "memory_history_mutated": False,
        "emitted_events": events,
    }


def analyze_fixture_bundles(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    active = bundles if bundles is not None else load_fixture_bundles()
    results: list[dict[str, object]] = []
    for bundle in active:
        results.append(process_reflection_bundle(bundle, observed_at=observed_at))
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "drb.advisory.fixture_bundles_analyzed",
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_memory_mutation": all(r.get("memory_history_mutated") is False for r in results),
        "permission_granted": False,
    }


__all__ = [
    "analyze_fixture_bundles",
    "consolidate_fragments",
    "create_counterfactual_scenario",
    "create_dream_fragments",
    "create_reflection_receipt",
    "process_reflection_bundle",
    "record_reflection_request",
    "refuse_drb_as_authority",
]
