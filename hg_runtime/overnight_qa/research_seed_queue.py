"""Research seed queue + selection policy.

Zero may PROPOSE/rank seeds. Ranking is advisory only. The runtime
approves/denies/modifies. Operator constraints override Zero's ranking. Some
seeds may be skipped; an incomplete queue is not a failure. No seed may require
completion of all other seeds. chosen_by_zero != approved_by_runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .research_seeds import build_research_seeds, ResearchSeed


SELECTION_FACTORS = (
    "novelty", "evidence_gap_importance", "testability", "source_availability",
    "mathematical_tractability", "operator_interest", "expected_value",
    "risk_of_woo_or_overclaim", "public_explainer_usefulness",
    "profile_model_diversity", "budget_cost",
)

DOCTRINE = (
    "Speculation is allowed. Promotion requires evidence.",
    "Wonder is allowed. Reverence is not authority.",
    "Pattern discovery is allowed. Numerology is not proof.",
    "A research seed is a question, not a conclusion.",
    "Zero may propose. The runtime disposes. The operator reviews.",
    "Consciousness markers are analytical metadata, not consciousness claims.",
    "Subjective experience is not automatically physical truth.",
    "CERN / LHC / collider claims require extraordinary evidence and falsifiable predictions.",
)


@dataclass
class ZeroSeedRanking:
    """Advisory only. Zero choosing a seed is NOT authorization."""
    seed_id: str
    rank: int
    rationale: str
    advisory_only: bool = True
    chosen_by_zero: bool = True
    approved_by_runtime: bool = False


@dataclass
class RuntimeSelectionDecision:
    seed_id: str
    decision: str  # approved / denied / modified / skipped
    reason: str
    budget: str = "small"
    completion_criteria: list[str] = field(default_factory=list)
    boundary_checks: list[str] = field(default_factory=list)
    output_namespace: str = ""
    evidence_requirements: list[str] = field(default_factory=list)
    promotion_forbidden: bool = True
    operator_review_required: bool = True
    runtime_approved: bool = False
    skipped_not_failed: bool = False


def build_queue() -> list[ResearchSeed]:
    return build_research_seeds()


def zero_rank_seeds(seed_ids: list[str]) -> list[ZeroSeedRanking]:
    """Simulate Zero proposing a ranking. Purely advisory."""
    rankings = []
    for i, sid in enumerate(seed_ids):
        rankings.append(ZeroSeedRanking(
            seed_id=sid, rank=i + 1,
            rationale="advisory proposal based on novelty/testability heuristic",
        ))
    return rankings


def runtime_select(
    ranking: ZeroSeedRanking,
    *,
    approve: bool,
    budget: str = "small",
    operator_override: bool = False,
) -> RuntimeSelectionDecision:
    """Runtime disposes. Operator override beats Zero ranking. Approval requires
    budget + completion criteria + boundary checks + evidence requirements.
    """
    seed = next((s for s in build_research_seeds() if s.seed_id == ranking.seed_id), None)
    if seed is None:
        return RuntimeSelectionDecision(
            seed_id=ranking.seed_id, decision="denied", reason="unknown seed",
            runtime_approved=False)

    if operator_override:
        return RuntimeSelectionDecision(
            seed_id=seed.seed_id, decision="denied",
            reason="operator constraint overrides Zero ranking",
            runtime_approved=False, skipped_not_failed=True)

    if not approve:
        return RuntimeSelectionDecision(
            seed_id=seed.seed_id, decision="skipped",
            reason="runtime deferred this seed; skipped is not failed",
            runtime_approved=False, skipped_not_failed=True)

    return RuntimeSelectionDecision(
        seed_id=seed.seed_id, decision="approved",
        reason="runtime approved with bounded budget and required checks",
        budget=budget,
        completion_criteria=seed.completion_criteria or ["bounded completion criteria required"],
        boundary_checks=seed.forbidden_promotions,
        output_namespace=f"overnight::seed::{seed.seed_id}",
        evidence_requirements=seed.evidence_requirements or ["evidence required before promotion"],
        promotion_forbidden=not seed.can_promote_to_knowledge,
        operator_review_required=True,
        runtime_approved=True,
    )


def selection_policy_snapshot() -> dict:
    return {
        "zero_ranking_is_advisory": True,
        "runtime_approval_required": True,
        "operator_constraints_override_zero": True,
        "incomplete_queue_is_not_failure": True,
        "no_seed_requires_all_others": True,
        "chosen_by_zero_is_not_approved_by_runtime": True,
        "selection_factors": list(SELECTION_FACTORS),
        "every_selected_seed_requires": [
            "budget", "completion_criteria", "boundary_checks",
            "output_namespace", "evidence_requirements",
            "promotion_forbidden_by_default",
        ],
        "doctrine": list(DOCTRINE),
    }


def incomplete_queue_is_failure(approved_count: int, total: int) -> bool:
    """An incomplete queue is never a failure."""
    return False
