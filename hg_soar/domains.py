"""SOAR Phase 1 domain evaluators — deterministic fixture rules, no I/O."""

from __future__ import annotations

from typing import Mapping

from hg_core.governance.capability_registry import lookup_capability
from hg_soar.types import DomainEvaluation, DomainId, proposal_content


def _stable_id(*parts: str) -> str:
    from hg_runtime.contract import stable_id

    return stable_id(*parts)

_DOMAIN_NAMES = {
    "D1": "safety",
    "D2": "perception",
    "D3": "memory",
    "D4": "task",
    "D5": "social",
    "D6": "learning",
    "D7": "sovereign",
}


def evaluate_domain(
    domain_id: DomainId,
    *,
    proposal: Mapping[str, object],
    input_refs: tuple[str, ...],
) -> DomainEvaluation:
    """Pure Phase 1 domain evaluation — fixture heuristics only."""
    proposal_id = str(proposal.get("payload", {}).get("proposal_id") or proposal.get("event_id"))
    evaluation_id = _stable_id("soar_eval", proposal_id, domain_id)
    content = proposal_content(proposal)
    capability_id = str(content.get("capability_id") or "cap.oea_stub_log")
    effect_class = str(content.get("effect_class") or "audit_log")
    capability = lookup_capability(capability_id)

    if domain_id == "D1":
        hard_veto = bool(content.get("hard_veto")) or (
            capability is not None and not capability.bind_allowed
        )
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d1_safety"),),
            confidence=1.0 if hard_veto else 0.9,
            verdict="HARD_VETO" if hard_veto else "CLEAR",
            reason_code="d1_hard_veto" if hard_veto else "d1_clear",
        )

    if domain_id == "D2":
        confidence = float(content.get("perception_confidence", 0.75))
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d2_perception"),),
            confidence=max(0.0, min(1.0, confidence)),
            verdict="PERCEPTION_OK",
            reason_code="d2_fixture",
        )

    if domain_id == "D3":
        stale = bool(content.get("memory_stale"))
        confidence = 0.35 if stale else 0.8
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d3_memory"),),
            confidence=confidence,
            verdict="STALE" if stale else "FRESH",
            reason_code="d3_stale" if stale else "d3_fresh",
        )

    if domain_id == "D4":
        kind = str(proposal.get("payload", {}).get("kind", ""))
        ok = kind == "candidate_action"
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d4_task"),),
            confidence=0.85 if ok else 0.2,
            verdict="TASK_PROPOSAL" if ok else "NOT_TASK",
            reason_code="d4_task_ok" if ok else "d4_not_task",
        )

    if domain_id == "D5":
        external = effect_class == "external_write"
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d5_social"),),
            confidence=0.4 if external else 0.7,
            verdict="SOCIAL_RISK" if external else "SOCIAL_OK",
            reason_code="d5_external_risk" if external else "d5_ok",
        )

    if domain_id == "D6":
        return DomainEvaluation(
            evaluation_id=evaluation_id,
            domain_id=domain_id,
            input_refs=input_refs,
            output_refs=(_stable_id("soar_sig", proposal_id, "d6_learning"),),
            confidence=0.6,
            verdict="ADVISORY",
            reason_code="d6_fixture",
        )

    # D7 domain record — vote summary for sovereign arbitration input
    return DomainEvaluation(
        evaluation_id=evaluation_id,
        domain_id=domain_id,
        input_refs=input_refs,
        output_refs=(_stable_id("soar_sig", proposal_id, "d7_sovereign"),),
        confidence=1.0,
        verdict="ARBITRATION_READY",
        reason_code="d7_ready",
    )


def evaluate_all_domains(
    *,
    proposal: Mapping[str, object],
    input_refs: tuple[str, ...],
) -> tuple[DomainEvaluation, ...]:
    return tuple(
        evaluate_domain(domain_id, proposal=proposal, input_refs=input_refs)
        for domain_id in ("D1", "D2", "D3", "D4", "D5", "D6", "D7")
    )


__all__ = ["evaluate_all_domains", "evaluate_domain"]
