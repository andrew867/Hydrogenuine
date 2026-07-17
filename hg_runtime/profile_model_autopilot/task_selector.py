"""Task selector / curiosity queue — bounded, consumes the research seed queue.

No unbounded 'do whatever' tasks. Curiosity is budgeted. Every task has
completion criteria, writes receipts, and can be skipped/denied. Source followup
requires source policy; knowledge promotion requires knowledge policy. Morning
operator review is required.
"""

from __future__ import annotations

from .schemas import TaskQueueItem


TASK_KINDS = (
    "proof_audit", "report_review", "evidence_gap_review", "knowledge_candidate_review",
    "source_followup", "moral_capsule_review", "public_claims_review",
    "regression_hypothesis", "document_verification", "prompt_verification",
    "research_seed_triage", "assumption_inversion", "falsification_design",
    "source_discovery", "operator_summary",
)


def build_curiosity_queue(max_tasks: int = 12) -> list[TaskQueueItem]:
    """Build a bounded curiosity queue from the research seed queue."""
    from hg_runtime.overnight_qa.research_seeds import build_research_seeds

    seeds = build_research_seeds()
    tasks: list[TaskQueueItem] = []

    for seed in seeds:
        if len(tasks) >= max_tasks:
            break
        requires_browsing = bool(getattr(seed, "can_browse_later", False))
        # Map a seed to a default task kind by its status.
        status = seed.hypothesis_status
        if status in ("speculative", "question", "conjecture", "toy_model"):
            kind = "assumption_inversion"
        elif status == "experiment_design":
            kind = "falsification_design"
        elif status == "source_discovery":
            kind = "source_discovery"
        elif status == "public_explainer":
            kind = "public_claims_review"
        elif status == "literature_review":
            kind = "evidence_gap_review"
        else:
            kind = "research_seed_triage"

        tasks.append(TaskQueueItem(
            task_id=f"task_{seed.seed_id}",
            task_kind=kind,
            research_seed_id=seed.seed_id,
            priority=getattr(seed, "priority_hint", "normal"),
            reason=f"bounded curiosity task for seed {seed.seed_id}",
            source="research_seed_queue",
            requires_browsing=requires_browsing,
            browsing_allowed=False,  # never allowed until source policy active
            requires_operator_review=True,
            token_budget=8000,
            wallclock_budget_seconds=900,
            max_profile_count=3,
            max_model_count=2,
            science_modes=list(getattr(seed, "model_lens_suggestions", []))[:0] or ["assume_real", "assume_false"],
            output_namespace=f"overnight::task::{seed.seed_id}",
            completion_criteria=getattr(seed, "completion_criteria", None)
                or ["bounded completion criteria required"],
        ))

    # Always end with a morning operator summary task.
    tasks.append(TaskQueueItem(
        task_id="task_morning_operator_summary",
        task_kind="operator_summary",
        priority="high",
        reason="mandatory morning operator review summary",
        source="autopilot",
        requires_operator_review=True,
        token_budget=4000, wallclock_budget_seconds=600,
        output_namespace="overnight::operator_summary",
        completion_criteria=["summary of attempted/skipped seeds; nothing promoted"],
    ))
    return tasks


def task_is_bounded(task: TaskQueueItem) -> bool:
    return (task.token_budget > 0 and task.wallclock_budget_seconds > 0
            and len(task.completion_criteria) > 0)


def all_tasks_bounded(tasks: list[TaskQueueItem]) -> bool:
    return all(task_is_bounded(t) for t in tasks)


def source_followup_requires_policy(task: TaskQueueItem) -> bool:
    if task.task_kind in ("source_followup", "source_discovery") or task.requires_browsing:
        return not task.browsing_allowed  # must remain gated
    return True


def morning_operator_review_present(tasks: list[TaskQueueItem]) -> bool:
    return any(t.task_kind == "operator_summary" for t in tasks)
