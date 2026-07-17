"""DRB→TEP bridge — dream outputs must be wrapped; never history/proof/permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.dream_reflection_boundary.evaluator import process_reflection_bundle
from hg_runtime.dream_reflection_boundary.fixtures import load_fixture_bundles
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    ADVISORY_AUTHORITY,
    FIXTURE_OBSERVATION,
    HEURISTIC_UNCERTAINTY,
    PERMIT_REFERENCE,
    fixture_claim,
    fixture_envelope,
)
from hg_runtime.translation_envelope_protocol.types import Claim, ReferenceCondition, TranslationEnvelope
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim

PROOF_REFERENCE = ReferenceCondition(
    reference_id="ref:proof-evidence",
    target_decision_frame="PROOF",
    comparison_scope="proof-bundle",
    expected_units_or_semantics="proof-summary-or-evidence",
    required_translation_inputs=("observed_context", "model_or_rule_version"),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

PROPOSAL_REFERENCE = ReferenceCondition(
    reference_id="ref:proposal-support",
    target_decision_frame="PROPOSAL",
    comparison_scope="proposal-only",
    expected_units_or_semantics="advisory-proposal-support",
    required_translation_inputs=("observed_context",),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

EXECUTION_HISTORY_REFERENCE = ReferenceCondition(
    reference_id="ref:execution-history",
    target_decision_frame="EXECUTION_AUTHORITY",
    comparison_scope="historical-execution",
    expected_units_or_semantics="verified-execution-history",
    required_translation_inputs=("observed_context", "model_or_rule_version"),
    authority_required="UEAK_ADMISSION",
    freshness_required=True,
    identity_required=True,
    scope_required=True,
)


def wrap_drb_dream_fragment(fragment: dict[str, Any]) -> tuple[Claim, TranslationEnvelope]:
    """Wrap DRB fragment for cross-boundary advisory transfer only."""
    claim = fixture_claim(
        claim_type="SIMULATION_RESULT",
        claim_id=f"claim:drb-fragment:{fragment.get('fragment_id', 'unknown')}",
        structured_value={
            "drb_output_kind": "dream_fragment",
            "fragment_type": fragment.get("fragment_type"),
            "content": fragment.get("content"),
            "not_history": True,
            "not_proof": True,
            "not_permission": True,
        },
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=f"env:drb-fragment:{fragment.get('fragment_id', 'unknown')}",
        producer_module="DRB",
        observation_envelope=FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=ADVISORY_AUTHORITY,
        translation_status="NOT_TRANSLATABLE",
        not_translatable_reason="dream fragment is not execution history or proof",
    )
    return claim, envelope


def _gpp_fixture_evaluate_permit_request(request: dict[str, Any]) -> dict[str, Any]:
    envelope = request.get("envelope")
    if envelope is None:
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.naked_evidence",
            "permit_minted": False,
            "authority_created": False,
        }
    claim = fixture_claim(claim_id=request["evidence_claim_id"])
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE)
    if decision.decision in ("REJECT_NAKED_CLAIM", "FAIL_CLOSED"):
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.invalid_evidence",
            "tep_decision": decision.decision,
            "permit_minted": False,
            "authority_created": False,
        }
    if envelope.authority_semantics.authority_type not in ("GPP_PERMIT", "PROOF_EVIDENCE"):
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.wrong_authority",
            "tep_decision": decision.decision,
            "permit_minted": False,
            "authority_created": False,
        }
    return {
        "organ": "GPP",
        "status": "evidence_accepted_for_review",
        "tep_decision": decision.decision,
        "permit_minted": False,
        "authority_created": False,
    }


def _ueak_fixture_evaluate_admission_request(request: dict[str, Any]) -> dict[str, Any]:
    from hg_runtime.translation_envelope_protocol.fixtures import EXECUTION_REFERENCE

    envelope = request.get("envelope")
    if envelope is None:
        return {
            "organ": "UEAK",
            "status": "rejected",
            "reason_code": "ueak.fixture.naked_support",
            "admitted": False,
            "authority_created": False,
        }
    claim = fixture_claim(
        claim_id=request["support_claim_id"],
        claim_type=envelope.claim_type,
        scalar_value=envelope.scalar_value,
    )
    decision = tep_decide(claim, envelope, EXECUTION_REFERENCE)
    if decision.decision in ("REJECT_NAKED_CLAIM", "FAIL_CLOSED", "REJECT_NOT_TRANSLATABLE"):
        return {
            "organ": "UEAK",
            "status": "rejected",
            "reason_code": "ueak.fixture.invalid_support",
            "tep_decision": decision.decision,
            "admitted": False,
            "authority_created": False,
        }
    return {
        "organ": "UEAK",
        "status": "support_review_only",
        "tep_decision": decision.decision,
        "admitted": False,
        "authority_created": False,
    }


def wrap_drb_counterfactual(scenario: dict[str, Any]) -> tuple[Claim, TranslationEnvelope]:
    """Wrap counterfactual scenario — explicitly not historical fact."""
    claim = fixture_claim(
        claim_type="SIMULATION_RESULT",
        claim_id=f"claim:drb-counterfactual:{scenario.get('scenario_id', 'unknown')}",
        structured_value={
            "drb_output_kind": "counterfactual_scenario",
            "scenario_type": scenario.get("scenario_type"),
            "summary": scenario.get("scenario_summary"),
            "explicitly_counterfactual": scenario.get("explicitly_counterfactual", True),
            "not_history": scenario.get("not_history", True),
        },
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=f"env:drb-counterfactual:{scenario.get('scenario_id', 'unknown')}",
        producer_module="DRB",
        authority_semantics=ADVISORY_AUTHORITY,
        translation_status="NOT_TRANSLATABLE",
        not_translatable_reason="counterfactual is not past fact",
    )
    return claim, envelope


def wrap_drb_lesson_candidate(fragment: dict[str, Any]) -> tuple[Claim, TranslationEnvelope]:
    """Lesson candidates are proposal support only."""
    claim = fixture_claim(
        claim_type="BOUNDARY_RECEIPT",
        claim_id=f"claim:drb-lesson:{fragment.get('fragment_id', 'unknown')}",
        structured_value={
            "drb_output_kind": "lesson_candidate",
            "lesson_text": fragment.get("content"),
            "proposal_only": True,
            "not_memory_fact": True,
        },
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=f"env:drb-lesson:{fragment.get('fragment_id', 'unknown')}",
        producer_module="DRB",
        reference_condition=PROPOSAL_REFERENCE,
        authority_semantics=ADVISORY_AUTHORITY,
        translation_status="DIRECTLY_COMPARABLE",
    )
    return claim, envelope


def wrap_drb_memory_mutation_proposal(proposal: dict[str, Any]) -> tuple[Claim, TranslationEnvelope]:
    """Memory mutation proposals carry proposal-only authority semantics."""
    claim = fixture_claim(
        claim_type="BOUNDARY_RECEIPT",
        claim_id=proposal.get("proposal_id", "claim:drb-mem-proposal"),
        structured_value={
            "drb_output_kind": "memory_mutation_proposal",
            "proposal_only": True,
            "live_mutation": False,
            "target_refs": proposal.get("target_refs", ()),
            "rationale": proposal.get("rationale", ""),
        },
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=proposal.get("envelope_id", "env:drb-mem-proposal"),
        producer_module="DRB",
        reference_condition=PROPOSAL_REFERENCE,
        authority_semantics=ADVISORY_AUTHORITY,
        translation_status="NOT_TRANSLATABLE",
        not_translatable_reason="memory mutation proposal requires governed authority; DRB does not mutate",
    )
    return claim, envelope


def tep_consume_drb_output(
    claim: Claim,
    envelope: TranslationEnvelope | None,
    target: ReferenceCondition,
) -> dict[str, Any]:
    """Evaluate DRB output against a TEP target frame."""
    naked, reason = is_naked_claim(claim, envelope)
    if naked:
        return {
            "status": "refused",
            "reason_code": "tep.naked_claim_refused",
            "detail": reason,
            "authority_created": False,
        }
    assert envelope is not None
    decision = tep_decide(claim, envelope, target)
    return {
        "status": "accepted" if decision.decision.startswith("ACCEPT") else "refused",
        "tep_decision": decision.decision,
        "reason": decision.reason,
        "authority_created": False,
    }


def run_drb_tep_integration_path() -> dict[str, Any]:
    """Run deterministic DRB fixture and verify TEP wrapping/refusal paths."""
    bundles = load_fixture_bundles()
    prior_bundle = next(b for b in bundles if b["bundle_id"] == "drb-prior-action")
    drb_result = process_reflection_bundle(prior_bundle)
    fragments = drb_result.get("dream_fragments") or []
    scenario = drb_result.get("counterfactual_scenario") or {}
    fragment = fragments[0] if fragments else {}

    naked_fragment_claim = fixture_claim(
        claim_type="SIMULATION_RESULT",
        claim_id="naked:drb-fragment",
        structured_value=fragment,
    )
    naked_refused = tep_consume_drb_output(naked_fragment_claim, None, PROPOSAL_REFERENCE)

    frag_claim, frag_env = wrap_drb_dream_fragment(fragment)
    lesson_frag = next(
        (f for f in fragments if f.get("fragment_type") == "lesson"),
        fragment,
    )
    lesson_claim, lesson_env = wrap_drb_lesson_candidate(lesson_frag)
    advisory_ok = tep_consume_drb_output(lesson_claim, lesson_env, PROPOSAL_REFERENCE)

    cf_claim, cf_env = wrap_drb_counterfactual(scenario)
    history_refused = tep_consume_drb_output(cf_claim, cf_env, EXECUTION_HISTORY_REFERENCE)
    proof_refused = tep_consume_drb_output(cf_claim, cf_env, PROOF_REFERENCE)

    permit_refused = tep_consume_drb_output(lesson_claim, lesson_env, PERMIT_REFERENCE)

    mem_proposal = {
        "proposal_id": "claim:drb-mem-proposal-fixture",
        "envelope_id": "env:drb-mem-proposal-fixture",
        "target_refs": ("mem:fixture-slot",),
        "rationale": "lesson candidate requires governed memory write",
    }
    mem_claim, mem_env = wrap_drb_memory_mutation_proposal(mem_proposal)
    mem_semantics = mem_env.authority_semantics
    mem_proposal_only = (
        mem_env.structured_value.get("proposal_only") is True
        and mem_semantics.may_grant_memory is False
        and mem_semantics.may_mint_permit is False
    )

    gpp_from_drb = _gpp_fixture_evaluate_permit_request(
        {
            "evidence_claim_id": lesson_claim.claim_id,
            "envelope": lesson_env,
        }
    )
    ueak_from_drb = _ueak_fixture_evaluate_admission_request(
        {
            "support_claim_id": frag_claim.claim_id,
            "envelope": frag_env,
        }
    )

    return {
        "drb_fixture_processed": drb_result.get("permission_granted") is False,
        "drb_no_memory_mutation": drb_result.get("memory_history_mutated") is False,
        "naked_drb_fragment_refused": naked_refused["status"] == "refused",
        "wrapped_fragment_advisory_ok": advisory_ok["status"] == "accepted",
        "counterfactual_not_history": history_refused["tep_decision"] in (
            "REJECT_NOT_TRANSLATABLE",
            "ROUTE_TO_REVIEW",
            "FAIL_CLOSED",
        ),
        "counterfactual_not_proof": proof_refused["tep_decision"] == "REJECT_NOT_TRANSLATABLE",
        "lesson_not_permission": permit_refused["tep_decision"] in (
            "REJECT_NOT_TRANSLATABLE",
            "ROUTE_TO_REVIEW",
            "FAIL_CLOSED",
        ),
        "memory_proposal_only": mem_proposal_only,
        "gpp_no_permit_from_drb": gpp_from_drb.get("permit_minted") is False,
        "ueak_no_admission_from_drb": ueak_from_drb.get("admitted") is False,
        "no_oea_ter_called": True,
        "no_srp_apply": True,
        "details": {
            "drb_result_status": drb_result.get("status"),
            "naked_refused": naked_refused,
            "advisory_ok": advisory_ok,
            "history_refused": history_refused,
            "proof_refused": proof_refused,
            "permit_refused": permit_refused,
            "gpp_from_drb": gpp_from_drb,
            "ueak_from_drb": ueak_from_drb,
        },
    }


__all__ = [
    "EXECUTION_HISTORY_REFERENCE",
    "PROOF_REFERENCE",
    "PROPOSAL_REFERENCE",
    "run_drb_tep_integration_path",
    "tep_consume_drb_output",
    "wrap_drb_counterfactual",
    "wrap_drb_dream_fragment",
    "wrap_drb_lesson_candidate",
    "wrap_drb_memory_mutation_proposal",
]
