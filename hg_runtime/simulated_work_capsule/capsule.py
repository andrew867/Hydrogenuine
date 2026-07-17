"""F12A simulated work capsule domain logic."""

from __future__ import annotations

from hg_runtime.simulated_work_capsule.schemas import (
    CAPSULE_TASK_DOMAINS,
    SimulatedWorkCapsuleError,
    reject_capsule_overreach,
)


def validate_capsule_task(task: dict) -> list[str]:
    issues = []
    if not task.get("task_id"):
        issues.append("missing_task_id")
    if task.get("domain") not in CAPSULE_TASK_DOMAINS:
        issues.append("invalid_domain")
    if not task.get("is_simulated"):
        issues.append("capsule_must_be_simulated")
    if task.get("real_customer"):
        issues.append("real_customer_forbidden")
    if task.get("customer_contact"):
        issues.append("customer_contact_forbidden")
    if task.get("live_submission"):
        issues.append("live_submission_forbidden")
    reject_capsule_overreach(task)
    return issues


def validate_work_plan(plan: dict) -> list[str]:
    issues = []
    if not plan.get("plan_id"):
        issues.append("missing_plan_id")
    if not plan.get("task_id"):
        issues.append("missing_task_id")
    if not plan.get("steps"):
        issues.append("missing_steps")
    for step in plan.get("steps", []):
        if not step.get("simulated"):
            issues.append("step_must_be_simulated")
    return issues


def validate_capsule_artifact(artifact: dict) -> list[str]:
    issues = []
    if not artifact.get("artifact_id"):
        issues.append("missing_artifact_id")
    if not artifact.get("is_simulated"):
        issues.append("artifact_must_be_simulated")
    if artifact.get("live_submission_target") is not None:
        issues.append("live_submission_target_forbidden")
    if artifact.get("social_post_target") is not None:
        issues.append("social_post_target_forbidden")
    if artifact.get("payment_target") is not None:
        issues.append("payment_target_forbidden")
    if artifact.get("invoice_target") is not None:
        issues.append("invoice_target_forbidden")
    return issues


def validate_review_packet(review: dict) -> list[str]:
    issues = []
    if not review.get("review_id"):
        issues.append("missing_review_id")
    if not review.get("operator_review_required"):
        issues.append("operator_review_must_be_required")
    if review.get("is_customer_acceptance"):
        issues.append("review_must_not_be_customer_acceptance")
    if review.get("is_payment_permission"):
        issues.append("review_must_not_be_payment_permission")
    if review.get("is_posting_permission"):
        issues.append("review_must_not_be_posting_permission")
    ve = review.get("value_estimate", {})
    if isinstance(ve, dict) and ve.get("is_payment_permission"):
        issues.append("value_estimate_must_not_be_payment_permission")
    return issues


def validate_state_memory_ref(ref: dict) -> list[str]:
    issues = []
    if not ref.get("f02_snapshot_ref"):
        issues.append("missing_f02_snapshot_ref")
    if ref.get("state_estimate_is_truth"):
        issues.append("state_estimate_must_not_be_truth")
    if ref.get("memory_is_evidence"):
        issues.append("memory_must_not_be_evidence")
    if ref.get("recommendation_is_permission"):
        issues.append("recommendation_must_not_be_permission")
    if ref.get("recommendation_is_patch_approval"):
        issues.append("recommendation_must_not_be_patch_approval")
    return issues


def generate_soak_workload(kind: str, count: int = 3) -> list[dict]:
    from hg_runtime.simulated_work_capsule.fixtures import fixture_capsule_task
    return [fixture_capsule_task(kind.upper()) for _ in range(count)]
