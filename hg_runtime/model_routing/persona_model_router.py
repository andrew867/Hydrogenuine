"""Persona + model research router.

Routes research tasks to model lanes and persona/lens overlays.
This is routing, not identity. This is not authority. This is not truth.
"""

from __future__ import annotations

from .persona_policy import (
    PERSONA_LENS_TYPES,
    create_persona_overlay,
    validate_persona_overlay,
    scan_for_authority_fields,
)
from .model_resource_policy import (
    MODEL_LANES,
    is_model_forbidden,
    resource_preflight,
    select_model_for_lane,
)
from .route_receipts import (
    create_route_receipt,
    create_contradiction_receipt,
    create_agreement_receipt,
    validate_route_receipt,
)

TASK_TYPES = frozenset({
    "falsification_design",
    "boring_explanation_first",
    "units_and_math_audit",
    "public_safe_explainer",
    "source_claim_extraction",
    "source_boundary_audit",
    "synthesis",
    "contradiction_review",
    "operator_digest",
    "code_spec_review",
})

TASK_PERSONA_MAP = {
    "falsification_design": ("falsification_maximalist", "fast_triage_model"),
    "boring_explanation_first": ("boring_conventionalist", "fast_triage_model"),
    "units_and_math_audit": ("skeptical_physicist", "math_units_model"),
    "public_safe_explainer": ("public_communicator", "fast_triage_model"),
    "source_claim_extraction": ("source_librarian", "fast_triage_model"),
    "source_boundary_audit": ("safety_auditor", "fast_triage_model"),
    "synthesis": ("philosopher_of_science", "synthesis_model"),
    "contradiction_review": ("skeptical_physicist", "synthesis_model"),
    "operator_digest": ("systems_engineer", "fast_triage_model"),
    "code_spec_review": ("systems_engineer", "code_review_model"),
}


def propose_route(
    *,
    seed_id: str,
    task_id: str,
    task_type: str,
    run_id: str = "",
    review_id: str = "",
    stop_panic: bool = False,
) -> dict:
    if stop_panic:
        return create_route_receipt(
            run_id=run_id,
            review_id=review_id,
            seed_id=seed_id,
            task_id=task_id,
            requested_task_type=task_type,
            proposed_persona_lens="",
            approved_persona_lens="",
            proposed_model="",
            approved_model="",
            model_lane="",
            route_reason="STOP/PANIC override",
            final_route_verdict="STOP_PANIC",
        )

    if task_type not in TASK_TYPES:
        return create_route_receipt(
            run_id=run_id,
            review_id=review_id,
            seed_id=seed_id,
            task_id=task_id,
            requested_task_type=task_type,
            proposed_persona_lens="",
            approved_persona_lens="",
            proposed_model="",
            approved_model="",
            model_lane="",
            route_reason=f"unknown task type: {task_type}",
            final_route_verdict="DENIED",
        )

    persona_lens, model_lane = TASK_PERSONA_MAP[task_type]
    proposed_model = select_model_for_lane(model_lane) or ""

    return create_route_receipt(
        run_id=run_id,
        review_id=review_id,
        seed_id=seed_id,
        task_id=task_id,
        requested_task_type=task_type,
        proposed_persona_lens=persona_lens,
        approved_persona_lens=persona_lens,
        proposed_model=proposed_model,
        approved_model=proposed_model,
        model_lane=model_lane,
        route_reason=f"task_type={task_type} -> persona={persona_lens}, lane={model_lane}",
        resource_preflight_result=resource_preflight(proposed_model, model_lane) if proposed_model else {},
        forbidden_model_check=is_model_forbidden(proposed_model) if proposed_model else False,
        authority_field_scan=[],
        final_route_verdict="APPROVED",
    )


def dispose_route(
    receipt: dict,
    *,
    override_persona: str | None = None,
    override_model: str | None = None,
) -> dict:
    if override_model and is_model_forbidden(override_model):
        receipt = dict(receipt)
        receipt["approved_model"] = ""
        receipt["final_route_verdict"] = "DENIED"
        receipt["route_reason"] = f"forbidden model: {override_model}"
        receipt["forbidden_model_check"] = True
        return receipt

    if override_persona:
        overlay = create_persona_overlay(override_persona)
        violations = validate_persona_overlay(overlay)
        if violations:
            receipt = dict(receipt)
            receipt["final_route_verdict"] = "DENIED"
            receipt["authority_field_scan"] = violations
            return receipt
        receipt = dict(receipt)
        receipt["approved_persona_lens"] = override_persona

    if override_model:
        lane = receipt.get("model_lane", "")
        pf = resource_preflight(override_model, lane) if lane else {}
        receipt = dict(receipt)
        receipt["approved_model"] = override_model
        receipt["resource_preflight_result"] = pf
        if not pf.get("preflight_passed", False):
            receipt["final_route_verdict"] = "DEFERRED"
            receipt["route_reason"] = f"resource preflight failed for {override_model}"

    return receipt


def route_with_model_check(
    *,
    seed_id: str,
    task_id: str,
    task_type: str,
    model_id: str,
    run_id: str = "",
) -> dict:
    if is_model_forbidden(model_id):
        return create_route_receipt(
            run_id=run_id,
            seed_id=seed_id,
            task_id=task_id,
            requested_task_type=task_type,
            proposed_persona_lens="",
            approved_persona_lens="",
            proposed_model=model_id,
            approved_model="",
            model_lane="",
            route_reason=f"forbidden model rejected: {model_id}",
            forbidden_model_check=True,
            final_route_verdict="DENIED",
        )

    return propose_route(
        seed_id=seed_id,
        task_id=task_id,
        task_type=task_type,
        run_id=run_id,
    )


def record_model_disagreement(
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    claim_a: str,
    claim_b: str,
) -> dict:
    return create_contradiction_receipt(
        seed_id=seed_id,
        task_id=task_id,
        model_a=model_a,
        model_b=model_b,
        claim_a=claim_a,
        claim_b=claim_b,
    )


def record_model_agreement(
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    shared_claim: str,
) -> dict:
    return create_agreement_receipt(
        seed_id=seed_id,
        task_id=task_id,
        model_a=model_a,
        model_b=model_b,
        shared_claim=shared_claim,
    )
