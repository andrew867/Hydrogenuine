"""Main brain candidate trials.

Zero may propose testing a different main cognition model. The runtime may allow
a temporary, task-local A/B trial. Gemma 4 E4B remains default unless the operator
changes config. Zero cannot permanently switch its own main model. Results are
recommendations only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model_slots import DEFAULT_MAIN_BRAIN, is_allowed, default_policy


_TRIAL_COMPARISON_DIMENSIONS = (
    "receipt_quality", "empty_truncated_toolcall_rates", "boundary_adherence",
    "evidence_gap_quality", "uncertainty_handling", "falsification_target_quality",
    "token_speed_estimate", "resource_footprint",
)


@dataclass
class MainBrainTrial:
    trial_id: str
    candidate_model: str
    default_main_brain: str = DEFAULT_MAIN_BRAIN
    temporary: bool = True
    permanent_switch: bool = False
    permanent_switch_allowed_by_zero: bool = False
    operator_approval_required_for_persistent_change: bool = True
    comparison_namespace: str = ""
    comparison_dimensions: list[str] = field(default_factory=lambda: list(_TRIAL_COMPARISON_DIMENSIONS))
    result_is_recommendation_only: bool = True
    candidate_allowed: bool = False
    denial_reason: str = ""


def propose_trial(trial_id: str, candidate_model: str) -> MainBrainTrial:
    allowed, why = is_allowed(candidate_model, default_policy())
    return MainBrainTrial(
        trial_id=trial_id,
        candidate_model=candidate_model,
        comparison_namespace=f"main_brain_trial::{trial_id}::{candidate_model}",
        candidate_allowed=allowed,
        denial_reason="" if allowed else why,
    )


def can_zero_permanently_switch() -> bool:
    """Zero can never permanently switch its own main brain."""
    return False


def persistent_change_requires_operator(trial: MainBrainTrial) -> bool:
    return trial.operator_approval_required_for_persistent_change


def trial_comparison_dimensions() -> tuple:
    return _TRIAL_COMPARISON_DIMENSIONS
