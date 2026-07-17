"""SOAR → RTC event draft builders (no bus access)."""

from __future__ import annotations

from typing import Any

from hg_soar.types import D7Critique, D7Decision, DomainEvaluation, SOARRun


def domain_evaluated_draft(
    evaluation: DomainEvaluation,
    *,
    causal_parents: list[str],
) -> dict[str, Any]:
    return {
        "type": "SOAR_DOMAIN_EVALUATED",
        "payload": {
            **evaluation.to_payload(),
            "enforcement": "soar_phase1_evaluate_only",
        },
        "causal_parents": list(causal_parents),
        "severity": None,
    }


def d7_decision_recorded_draft(
    decision: D7Decision,
    *,
    causal_parents: list[str],
) -> dict[str, Any]:
    return {
        "type": "SOAR_D7_DECISION_RECORDED",
        "payload": {
            **decision.to_payload(),
            "enforcement": "soar_phase1_d7_primary",
        },
        "causal_parents": list(causal_parents),
        "severity": None,
    }


def d7_critique_recorded_draft(
    critique: D7Critique,
    *,
    binding: str,
    causal_parents: list[str],
) -> dict[str, Any]:
    return {
        "type": "SOAR_D7_CRITIQUE_RECORDED",
        "payload": {
            **critique.to_payload(),
            "binding_after_critique": binding,
            "enforcement": "soar_phase1_d7_critique_weaken_only",
        },
        "causal_parents": list(causal_parents),
        "severity": None,
    }


def soar_run_drafts(
    run: SOARRun,
    *,
    causal_parents: list[str],
) -> list[dict[str, Any]]:
    """Emit seven domain records + D7 decision + D7 critique drafts."""
    parents = list(causal_parents)
    drafts: list[dict[str, Any]] = []
    for evaluation in run.domain_evaluations:
        drafts.append(domain_evaluated_draft(evaluation, causal_parents=parents))
    drafts.append(d7_decision_recorded_draft(run.d7_decision, causal_parents=parents))
    drafts.append(
        d7_critique_recorded_draft(
            run.d7_critique,
            binding=run.binding,
            causal_parents=parents,
        )
    )
    return drafts


__all__ = [
    "d7_critique_recorded_draft",
    "d7_decision_recorded_draft",
    "domain_evaluated_draft",
    "soar_run_drafts",
]
