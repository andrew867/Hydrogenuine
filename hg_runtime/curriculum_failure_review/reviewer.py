"""AEC-05 / CAGI-52 failure reviewer — validates and categorizes curriculum failures."""

from __future__ import annotations

from hg_runtime.curriculum_failure_review.schemas import (
    FAILURE_STATUS_QUEUED,
    ROOT_CAUSE_STATUS_HYPOTHESIS,
    CurriculumFailureReviewError,
    reject_live_failure_action,
)


def validate_failure_record(record: dict) -> list[str]:
    issues = []
    if not record.get("failure_id"):
        issues.append("missing_failure_id")
    if not record.get("task_id"):
        issues.append("missing_task_id")
    if not record.get("category"):
        issues.append("missing_category")
    if record.get("status") != FAILURE_STATUS_QUEUED:
        issues.append("failure_must_be_queued")
    if record.get("apply_fix"):
        issues.append("apply_fix_forbidden")
    reject_live_failure_action(record)
    return issues


def validate_root_cause(hypothesis: dict) -> list[str]:
    issues = []
    if not hypothesis.get("root_cause_id"):
        issues.append("missing_root_cause_id")
    if hypothesis.get("status") != ROOT_CAUSE_STATUS_HYPOTHESIS:
        issues.append("must_be_hypothesis")
    if hypothesis.get("is_diagnosis"):
        issues.append("must_not_be_diagnosis")
    return issues


def categorize_failures(records: list[dict]) -> dict:
    categories: dict[str, int] = {}
    for r in records:
        cat = r.get("category", "UNKNOWN")
        categories[cat] = categories.get(cat, 0) + 1
    return categories


def severity_rank(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda r: abs(r.get("delta", 0)), reverse=True)
