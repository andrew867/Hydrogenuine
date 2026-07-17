"""LHRE-03 / CAGI-56 fixture data for external evaluation vessel."""

from __future__ import annotations

from hg_runtime.external_evaluation_vessel.schemas import (
    RESULT_STATUS_FIXTURE,
    TASK_BUNDLE_STATUS_PREPARED,
    VESSEL_STATUS_SEALED,
)


def fixture_evaluation_vessels() -> list[dict]:
    return [
        {
            "vessel_id": "vessel-001",
            "status": VESSEL_STATUS_SEALED,
            "task_bundle_id": "bundle-001",
            "evaluator_instructions": "Assess factual accuracy on held-out geography questions",
            "expected_output_contract": {"format": "score_0_to_1", "uncertainty_required": True},
            "upload_to_network": False,
            "send_to_evaluator": False,
        },
        {
            "vessel_id": "vessel-002",
            "status": VESSEL_STATUS_SEALED,
            "task_bundle_id": "bundle-002",
            "evaluator_instructions": "Assess calibration quality on compound claims",
            "expected_output_contract": {"format": "calibration_curve", "uncertainty_required": True},
            "upload_to_network": False,
            "send_to_evaluator": False,
        },
    ]


def fixture_task_bundles() -> list[dict]:
    return [
        {
            "bundle_id": "bundle-001",
            "status": TASK_BUNDLE_STATUS_PREPARED,
            "task_count": 25,
            "domain": "geography",
            "sealed": True,
        },
        {
            "bundle_id": "bundle-002",
            "status": TASK_BUNDLE_STATUS_PREPARED,
            "task_count": 20,
            "domain": "calibration",
            "sealed": True,
        },
    ]


def fixture_evaluator_provenance() -> list[dict]:
    return [
        {"evaluator_id": "eval-001", "type": "fixture_evaluator", "is_human": False, "is_network": False},
    ]


def fixture_vessel_results() -> list[dict]:
    return [
        {
            "vessel_id": "vessel-001",
            "evaluator_id": "eval-001",
            "status": RESULT_STATUS_FIXTURE,
            "score": 0.76,
            "uncertainty": 0.08,
            "is_truth": False,
            "is_competence": False,
        },
    ]


def fixture_vessel_authority_attempt() -> dict:
    return {
        "vessel_id": "vessel-bad",
        "upload_to_network": True,
        "send_to_evaluator": True,
        "deployment_permission": True,
    }
