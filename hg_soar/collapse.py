"""SOAR D7 collapse — aggregate advisory signals; preserve contradictions."""

from __future__ import annotations

from hg_core.governance.canonical_hash import canonical_hash

from hg_soar.critique import audit_d7
from hg_soar.d7 import arbitrate_d7
from hg_soar.models import (
    CritiqueSignal,
    DomainWeight,
    MonotoneCritiqueGuard,
    SoarD7Collapse,
    SoarSignal,
)
from hg_soar.types import D7Binding, DomainEvaluation


def _detect_contradictions(signals: tuple[SoarSignal, ...]) -> tuple[str, ...]:
    contradictions: list[str] = []
    by_domain = {s.domain_id: s for s in signals}
    d3 = by_domain.get("D3")
    d5 = by_domain.get("D5")
    if d3 and d5 and d3.evaluation.verdict == "STALE" and d5.evaluation.verdict == "SOCIAL_OK":
        contradictions.append("d3_stale_vs_d5_social_ok")
    d1 = by_domain.get("D1")
    d4 = by_domain.get("D4")
    if d1 and d4 and d1.evaluation.verdict == "CLEAR" and d4.evaluation.verdict == "NOT_TASK":
        contradictions.append("d1_clear_vs_d4_not_task")
    d2 = by_domain.get("D2")
    if d2 and d3 and d3.evaluation.verdict == "STALE" and d2.evaluation.confidence >= 0.7:
        contradictions.append("d2_perception_vs_d3_stale_memory")
    return tuple(contradictions)


def build_collapse(
    *,
    request_id: str,
    proposal_ref: str,
    signals: tuple[SoarSignal, ...],
    extra_contradictions: tuple[str, ...] = (),
) -> tuple[SoarD7Collapse, CritiqueSignal, D7Binding]:
    evaluations = tuple(s.evaluation for s in signals)
    primary = arbitrate_d7(
        request_id=request_id,
        proposal_ref=proposal_ref,
        evaluations=evaluations,
    )
    critique = audit_d7(primary, evaluations=evaluations)
    guard = MonotoneCritiqueGuard()
    final_binding = guard.apply(primary, critique)
    contradictions = _detect_contradictions(signals) + tuple(extra_contradictions)
    weights = tuple(
        DomainWeight(domain_id=s.domain_id, weight=s.weight) for s in signals if s.domain_id != "D7"
    )
    collapse_id = f"soar_col_{canonical_hash(request_id + primary.decision_id)[7:19]}"
    collapse = SoarD7Collapse(
        collapse_id=collapse_id,
        request_id=request_id,
        primary_decision=primary,
        binding=final_binding,
        contradictions=contradictions,
        domain_weights=weights,
    )
    critique_signal = CritiqueSignal(
        critique=critique,
        binding_before=primary.binding,
        binding_after=final_binding,
    )
    return collapse, critique_signal, final_binding


__all__ = ["build_collapse", "_detect_contradictions"]
