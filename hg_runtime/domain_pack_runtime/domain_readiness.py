"""Domain readiness evaluation."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.domain_pack_record import build_domain_pack_readiness_record
from hg_runtime.domain_pack_runtime.schemas import DomainPackBatchBoundaryError


def evaluate_readiness_state(
    pack: dict,
    *,
    boundary_record: dict | None = None,
    refused: bool = False,
) -> str:
    if refused or boundary_record and boundary_record.get("refusal_reasons"):
        return "REFUSED_BY_BOUNDARY"
    if not pack.get("provenance_refs"):
        return "NOT_READY"
    if pack.get("skill_ids") and pack.get("boundary_tags"):
        return "READY_FOR_REVIEW"
    return "NOT_READY"


def build_readiness_record_for_pack(
    pack: dict,
    boundary_record: dict | None = None,
    *,
    refused: bool = False,
) -> dict:
    state = evaluate_readiness_state(pack, boundary_record=boundary_record, refused=refused)
    if state not in {"NOT_READY", "READY_FOR_REVIEW", "REFUSED_BY_BOUNDARY"}:
        raise DomainPackBatchBoundaryError(f"invalid_readiness_state:{state}")
    notes = []
    refusal_reason = None
    if state == "READY_FOR_REVIEW":
        notes.append("pack_has_skills_and_boundaries_for_operator_review")
    elif state == "REFUSED_BY_BOUNDARY":
        refusal_reason = "boundary_refusal_recorded"
        notes.append("readiness_refused_by_boundary")
    else:
        notes.append("pack_not_ready_for_review")
    return build_domain_pack_readiness_record(
        readiness_id=f"readiness-{pack['pack_id']}",
        pack_id=pack["pack_id"],
        readiness_state=state,
        review_notes=notes,
        refusal_reason=refusal_reason,
    )
