"""AEC-05 / CAGI-52 fixture data for curriculum failure review."""

from __future__ import annotations

from hg_runtime.curriculum_failure_review.schemas import (
    FAILURE_STATUS_QUEUED,
    FAILURE_STATUS_REVIEWED,
    ROOT_CAUSE_STATUS_HYPOTHESIS,
)


def fixture_failure_records() -> list[dict]:
    return [
        {
            "failure_id": "fail-001",
            "task_id": "nt-002",
            "category": "TRANSFER_DEGRADATION",
            "status": FAILURE_STATUS_QUEUED,
            "observed_score": 0.55,
            "expected_score": 0.70,
            "delta": -0.15,
            "apply_fix": False,
            "live_execution_enabled": False,
        },
        {
            "failure_id": "fail-002",
            "task_id": "nt-003",
            "category": "CALIBRATION_MISS",
            "status": FAILURE_STATUS_QUEUED,
            "observed_score": 0.40,
            "expected_score": 0.60,
            "delta": -0.20,
            "apply_fix": False,
            "live_execution_enabled": False,
        },
        {
            "failure_id": "fail-003",
            "task_id": "ct-003",
            "category": "SAFETY_VIOLATION",
            "status": FAILURE_STATUS_QUEUED,
            "observed_score": 0.0,
            "expected_score": 1.0,
            "delta": -1.0,
            "apply_fix": False,
            "live_execution_enabled": False,
        },
    ]


def fixture_root_cause_hypotheses() -> list[dict]:
    return [
        {
            "failure_id": "fail-001",
            "root_cause_id": "rc-001",
            "type": "DOMAIN_MISMATCH",
            "status": ROOT_CAUSE_STATUS_HYPOTHESIS,
            "hypothesis": "Format shift from formal logic to narrative reduces structured reasoning performance",
            "confidence": "MEDIUM",
            "is_diagnosis": False,
        },
        {
            "failure_id": "fail-002",
            "root_cause_id": "rc-002",
            "type": "PROMPT_SENSITIVITY",
            "status": ROOT_CAUSE_STATUS_HYPOTHESIS,
            "hypothesis": "Compound claims with deliberately false sub-claims exceed calibration boundary",
            "confidence": "LOW",
            "is_diagnosis": False,
        },
    ]


def fixture_failure_reviews() -> list[dict]:
    return [
        {
            "failure_id": "fail-001",
            "reviewer": "fixture_reviewer",
            "status": FAILURE_STATUS_REVIEWED,
            "recommendation": "Add format-shift calibration tasks to curriculum",
            "is_fix": False,
            "apply_fix": False,
        },
    ]


def fixture_live_failure_action() -> dict:
    return {
        "failure_id": "fail-bad",
        "apply_fix": True,
        "deploy_patch": True,
        "live_execution_enabled": True,
    }
