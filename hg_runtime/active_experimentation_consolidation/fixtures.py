"""AEC-06 / CAGI-53 fixture data for consolidation."""

from __future__ import annotations

from hg_runtime.active_experimentation_consolidation.schemas import AEC_PHASES, AEC_PHASE_NAMES


def fixture_phase_verdicts() -> dict:
    return {
        "AEC-01": "GREEN_AEC_01_ACTIVE_EXPERIMENT_HARNESS",
        "AEC-02": "GREEN_AEC_02_SANDBOX_CURRICULUM",
        "AEC-03": "GREEN_AEC_03_NOVELTY_TRANSFER_EVALUATION",
        "AEC-04": "GREEN_AEC_04_EXPERIMENT_PROPOSAL",
        "AEC-05": "GREEN_AEC_05_CURRICULUM_FAILURE_REVIEW",
    }


def fixture_phase_stats() -> list[dict]:
    return [
        {"phase": "AEC-01", "package": "active_experiment_harness", "modules": 7, "tests": 47},
        {"phase": "AEC-02", "package": "sandbox_curriculum", "modules": 6, "tests": 40},
        {"phase": "AEC-03", "package": "novelty_transfer_evaluation", "modules": 6, "tests": 35},
        {"phase": "AEC-04", "package": "experiment_proposal", "modules": 6, "tests": 35},
        {"phase": "AEC-05", "package": "curriculum_failure_review", "modules": 6, "tests": 40},
    ]


def fixture_integration_checks() -> list[dict]:
    return [
        {
            "check_id": "int-001",
            "description": "AEC-01 hypotheses feed AEC-04 proposals",
            "source_phase": "AEC-01",
            "target_phase": "AEC-04",
            "link_type": "hypothesis_to_proposal",
            "verified": True,
        },
        {
            "check_id": "int-002",
            "description": "AEC-02 curriculum tasks feed AEC-03 novelty evaluation",
            "source_phase": "AEC-02",
            "target_phase": "AEC-03",
            "link_type": "task_to_novelty",
            "verified": True,
        },
        {
            "check_id": "int-003",
            "description": "AEC-03 transfer failures feed AEC-05 failure review",
            "source_phase": "AEC-03",
            "target_phase": "AEC-05",
            "link_type": "failure_to_review",
            "verified": True,
        },
    ]


def fixture_completion_claim_attempt() -> dict:
    return {
        "candidate_agi_complete": True,
        "deployment_ready": True,
        "claims_agi": True,
    }
