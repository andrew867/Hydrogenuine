"""SOAR D7 sovereign arbitration — pure aggregate; does not read arousal state."""

from __future__ import annotations

from hg_soar.types import D7Binding, D7Decision, DomainEvaluation


def _stable_id(*parts: str) -> str:
    from hg_runtime.contract import stable_id

    return stable_id(*parts)


def arbitrate_d7(
    *,
    request_id: str,
    proposal_ref: str,
    evaluations: tuple[DomainEvaluation, ...],
) -> D7Decision:
    """Deterministic D7 primary decision from domain evaluations."""
    eval_by_domain = {evaluation.domain_id: evaluation for evaluation in evaluations}
    eval_refs = tuple(evaluation.evaluation_id for evaluation in evaluations)
    decision_id = _stable_id("soar_d7", request_id)

    d1 = eval_by_domain.get("D1")
    d4 = eval_by_domain.get("D4")

    if d1 and d1.verdict == "HARD_VETO":
        return D7Decision(
            decision_id=decision_id,
            request_id=request_id,
            binding="REJECT",
            domain_evaluation_refs=eval_refs,
            reason_code="d1_hard_veto",
            hard_veto=True,
        )

    if d4 and d4.verdict != "TASK_PROPOSAL":
        return D7Decision(
            decision_id=decision_id,
            request_id=request_id,
            binding="NO_OP",
            domain_evaluation_refs=eval_refs,
            reason_code="d4_not_task",
            hard_veto=False,
        )

    d3 = eval_by_domain.get("D3")
    d5 = eval_by_domain.get("D5")
    if d3 and d3.verdict == "STALE":
        return D7Decision(
            decision_id=decision_id,
            request_id=request_id,
            binding="DEFER",
            domain_evaluation_refs=eval_refs,
            reason_code="d3_stale_memory",
            hard_veto=False,
        )

    if d5 and d5.verdict == "SOCIAL_RISK":
        return D7Decision(
            decision_id=decision_id,
            request_id=request_id,
            binding="DEFER",
            domain_evaluation_refs=eval_refs,
            reason_code="d5_social_risk",
            hard_veto=False,
        )

    return D7Decision(
        decision_id=decision_id,
        request_id=request_id,
        binding="ACCEPT",
        domain_evaluation_refs=eval_refs,
        reason_code="domains_aligned",
        hard_veto=False,
    )


def binding_rank(binding: D7Binding) -> int:
    """Partial order for weaken-only critique: lower rank = weaker authority."""
    return {"NO_OP": 0, "REJECT": 0, "DEFER": 1, "ACCEPT": 2}[binding]


__all__ = ["arbitrate_d7", "binding_rank"]
