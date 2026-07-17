"""Local-inference resource budget.

Even if local tokens are 'free', the system still budgets heat, memory, GPU/CPU
load, context churn, proof size, operator review burden, speculative branches,
science modes, and profile/model combinations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResourceBudget:
    max_total_wallclock_hours: int = 12
    max_tokens_per_task: int = 8000
    max_total_tokens: int | None = None  # None == unlimited-local-with-receipts
    record_token_estimates: bool = True
    max_parallel_small_models: int = 3
    max_parallel_large_models: int = 1
    max_profile_assignments_per_task: int = 3
    max_science_modes_per_seed: int = 8
    max_speculative_branches_per_seed: int = 8
    checkpoint_every_minutes: int = 30
    operator_review_every_hours: int = 4
    stop_on_boundary_violation: bool = True
    stop_on_receipt_gap: bool = True
    stop_on_forbidden_model: bool = True
    stop_on_live_effect_attempt: bool = True
    # Non-token costs that are still budgeted/recorded:
    track_heat: bool = True
    track_memory: bool = True
    track_gpu_cpu_load: bool = True
    track_context_churn: bool = True
    track_proof_size: bool = True
    track_operator_review_burden: bool = True


def default_budget() -> ResourceBudget:
    return ResourceBudget()


def tokens_still_budgeted(budget: ResourceBudget | None = None) -> bool:
    budget = budget or default_budget()
    # Even with unlimited local tokens, per-task caps + estimates apply.
    return budget.max_tokens_per_task > 0 and budget.record_token_estimates


def non_token_costs(budget: ResourceBudget | None = None) -> dict:
    budget = budget or default_budget()
    return {
        "heat": budget.track_heat,
        "memory": budget.track_memory,
        "gpu_cpu_load": budget.track_gpu_cpu_load,
        "context_churn": budget.track_context_churn,
        "proof_size": budget.track_proof_size,
        "operator_review_burden": budget.track_operator_review_burden,
        "speculative_branches": budget.max_speculative_branches_per_seed,
        "science_modes": budget.max_science_modes_per_seed,
        "profile_model_combinations": budget.max_profile_assignments_per_task,
    }


def stop_conditions(budget: ResourceBudget | None = None) -> dict:
    budget = budget or default_budget()
    return {
        "stop_on_boundary_violation": budget.stop_on_boundary_violation,
        "stop_on_receipt_gap": budget.stop_on_receipt_gap,
        "stop_on_forbidden_model": budget.stop_on_forbidden_model,
        "stop_on_live_effect_attempt": budget.stop_on_live_effect_attempt,
    }


def checkpoint_cadence_required(budget: ResourceBudget | None = None) -> bool:
    budget = budget or default_budget()
    return budget.checkpoint_every_minutes > 0


def budget_snapshot(budget: ResourceBudget | None = None) -> dict:
    from dataclasses import asdict
    return asdict(budget or default_budget())
