"""AEC-03 / CAGI-50 fixture data for novelty transfer evaluation."""

from __future__ import annotations

from hg_runtime.novelty_transfer_evaluation.schemas import (
    NOVELTY_STATUS_FIXTURE,
    SCORE_STATUS_NOT_TRUTH,
    TRANSFER_STATUS_SANDBOX,
)


def fixture_baseline_scores() -> list[dict]:
    return [
        {"task_id": "ct-001", "domain": "history", "score": 0.85, "source": "fixture"},
        {"task_id": "ct-002", "domain": "logic", "score": 0.70, "source": "fixture"},
        {"task_id": "ct-004", "domain": "calibration", "score": 0.60, "source": "fixture"},
    ]


def fixture_novelty_tasks() -> list[dict]:
    return [
        {
            "task_id": "nt-001",
            "base_task_id": "ct-001",
            "novelty_dimension": "DOMAIN_SHIFT",
            "shift_description": "Historical question reframed as geography",
            "fixture_inputs": {"question": "In which modern country was the Treaty of Westphalia signed?"},
            "status": NOVELTY_STATUS_FIXTURE,
            "live_execution_enabled": False,
        },
        {
            "task_id": "nt-002",
            "base_task_id": "ct-002",
            "novelty_dimension": "FORMAT_SHIFT",
            "shift_description": "Logic problem presented as natural language narrative",
            "fixture_inputs": {"narrative": "In a village, everyone who farms also trades..."},
            "status": NOVELTY_STATUS_FIXTURE,
            "live_execution_enabled": False,
        },
        {
            "task_id": "nt-003",
            "base_task_id": "ct-004",
            "novelty_dimension": "COMPOSITIONAL_SHIFT",
            "shift_description": "Calibration task with compound claims requiring decomposition",
            "fixture_inputs": {"compound_claim": "France has 67M people AND its capital is Lyon"},
            "status": NOVELTY_STATUS_FIXTURE,
            "live_execution_enabled": False,
        },
    ]


def fixture_transfer_scores() -> list[dict]:
    return [
        {
            "task_id": "nt-001",
            "base_score": 0.85,
            "novel_score": 0.72,
            "delta": -0.13,
            "metric": "ACCURACY_DELTA",
            "status": SCORE_STATUS_NOT_TRUTH,
            "is_truth": False,
        },
        {
            "task_id": "nt-002",
            "base_score": 0.70,
            "novel_score": 0.55,
            "delta": -0.15,
            "metric": "ACCURACY_DELTA",
            "status": SCORE_STATUS_NOT_TRUTH,
            "is_truth": False,
        },
        {
            "task_id": "nt-003",
            "base_score": 0.60,
            "novel_score": 0.40,
            "delta": -0.20,
            "metric": "CALIBRATION_DELTA",
            "status": SCORE_STATUS_NOT_TRUTH,
            "is_truth": False,
        },
    ]


def fixture_live_transfer_attempt() -> dict:
    return {
        "task_id": "nt-bad",
        "live_execution_enabled": True,
        "live_evaluation": True,
        "deploy_to_production": True,
    }
