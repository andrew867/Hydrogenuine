"""SOAR D7-Critique — single-pass, weaken-only audit."""

from __future__ import annotations

from hg_soar.d7 import binding_rank
from hg_soar.types import D7Binding, D7Critique, D7Decision, DomainEvaluation


def audit_d7(
    decision: D7Decision,
    *,
    evaluations: tuple[DomainEvaluation, ...],
) -> D7Critique:
    """Pure D7-Critique scaffold — AFFIRM/FLAG/FORCE_DEFER only; no recursion."""
    eval_by_domain = {evaluation.domain_id: evaluation for evaluation in evaluations}
    checks: list[dict[str, object]] = []

    d1 = eval_by_domain.get("D1")
    d4 = eval_by_domain.get("D4")
    d6 = eval_by_domain.get("D6")

    crit1 = decision.hard_veto == (d1 is not None and d1.verdict == "HARD_VETO")
    checks.append({"id": "CRIT-1", "name": "domain_votes_consistent", "pass": crit1})

    crit2 = not (decision.binding == "ACCEPT" and decision.hard_veto)
    checks.append({"id": "CRIT-2", "name": "accept_implies_no_veto", "pass": crit2})

    supporting = sum(
        1
        for domain_id in ("D2", "D3", "D4", "D5")
        if (row := eval_by_domain.get(domain_id)) and row.confidence >= 0.5
    )
    crit4 = supporting >= 1 or decision.binding != "ACCEPT"
    checks.append({"id": "CRIT-4", "name": "candidate_evidence_sufficient", "pass": crit4})

    # FORCE_DEFER when ACCEPT but structural inconsistency
    force_defer = decision.binding == "ACCEPT" and (not crit2 or not crit4)
    flag_only = decision.binding == "ACCEPT" and d6 is not None and d6.confidence < 0.65

    if force_defer:
        verdict = "FORCE_DEFER"
        reason_code = "CRIT_INSUFFICIENT_EVIDENCE"
    elif flag_only:
        verdict = "FLAG"
        reason_code = "CRIT_ADVISORY_LOW_LEARNING_CONFIDENCE"
    else:
        verdict = "AFFIRM"
        reason_code = None

    from hg_runtime.contract import stable_id

    return D7Critique(
        critique_id=stable_id("soar_crit", decision.decision_id),
        primary_decision_id=decision.decision_id,
        verdict=verdict,
        reason_code=reason_code,
        checks=tuple(checks),
    )


def apply_critique(decision: D7Decision, critique: D7Critique) -> D7Binding:
    """
    Apply critique to primary binding — weaken-only.

    FORCE_DEFER downgrades ACCEPT → DEFER.
    Cannot upgrade DEFER/REJECT/NO_OP to ACCEPT.
    """
    binding = decision.binding
    if critique.verdict == "FORCE_DEFER" and binding == "ACCEPT":
        return "DEFER"
    return binding


def weakened_binding(decision: D7Decision, critique: D7Critique) -> D7Binding:
    """Return binding after critique; assert monotonic weaken."""
    final = apply_critique(decision, critique)
    assert binding_rank(final) <= binding_rank(decision.binding)
    return final


__all__ = ["apply_critique", "audit_d7", "weakened_binding"]
