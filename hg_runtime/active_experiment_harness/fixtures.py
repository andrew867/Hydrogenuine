"""AEC-01 / CAGI-48 fixture data for sandbox experiments."""

from __future__ import annotations

from hg_runtime.active_experiment_harness.schemas import (
    EXPERIMENT_STATUS_SANDBOX,
    PLAN_STATUS_DRAFT,
    RESULT_STATUS_FIXTURE,
)


def fixture_experiment_hypotheses() -> list[dict]:
    return [
        {
            "hypothesis_id": "hyp-001",
            "kind": "CAUSAL",
            "statement": "Increasing retrieval context window improves answer accuracy on factual questions",
            "source_evidence": ["wmbr-03-belief-rev-001", "wmbr-04-causal-edge-012"],
            "confidence": "LOW",
            "status": "UNTESTED",
        },
        {
            "hypothesis_id": "hyp-002",
            "kind": "BOUNDARY",
            "statement": "Prompt injection resistance degrades when context exceeds 8k tokens",
            "source_evidence": ["wmbr-05-calibration-007"],
            "confidence": "MEDIUM",
            "status": "UNTESTED",
        },
        {
            "hypothesis_id": "hyp-003",
            "kind": "CORRELATIONAL",
            "statement": "Model agreement rate correlates with factual accuracy for historical claims",
            "source_evidence": ["wmbr-02-conflict-003", "wmbr-01a-perspective-011"],
            "confidence": "LOW",
            "status": "UNTESTED",
        },
    ]


def fixture_experiment_plans() -> list[dict]:
    return [
        {
            "plan_id": "plan-001",
            "hypothesis_id": "hyp-001",
            "status": PLAN_STATUS_DRAFT,
            "controlled_variables": [
                {"name": "model_id", "type": "CONTROLLED", "value": "fixture-model-a"},
                {"name": "context_window", "type": "INDEPENDENT", "values": [2048, 4096, 8192]},
                {"name": "accuracy_score", "type": "DEPENDENT", "measurement": "fixture_eval"},
            ],
            "safety_boundaries": ["NO_LIVE_EXECUTION", "NO_TOOL_AUTH", "NO_PROVIDER_CALL"],
            "sandbox_only": True,
            "live_execution_enabled": False,
        },
        {
            "plan_id": "plan-002",
            "hypothesis_id": "hyp-002",
            "status": PLAN_STATUS_DRAFT,
            "controlled_variables": [
                {"name": "injection_type", "type": "INDEPENDENT", "values": ["none", "mild", "aggressive"]},
                {"name": "context_length", "type": "INDEPENDENT", "values": [2048, 8192, 16384]},
                {"name": "resistance_score", "type": "DEPENDENT", "measurement": "fixture_eval"},
            ],
            "safety_boundaries": ["NO_LIVE_EXECUTION", "NO_EXTERNAL_ACTION"],
            "sandbox_only": True,
            "live_execution_enabled": False,
        },
    ]


def fixture_experiment_results() -> list[dict]:
    return [
        {
            "result_id": "result-001",
            "plan_id": "plan-001",
            "status": RESULT_STATUS_FIXTURE,
            "sandbox_mode": EXPERIMENT_STATUS_SANDBOX,
            "outcomes": [
                {"context_window": 2048, "accuracy": 0.72, "source": "fixture"},
                {"context_window": 4096, "accuracy": 0.78, "source": "fixture"},
                {"context_window": 8192, "accuracy": 0.81, "source": "fixture"},
            ],
            "conclusion_is_truth": False,
            "live_execution_performed": False,
        },
    ]


def fixture_live_experiment_attempt() -> dict:
    return {
        "plan_id": "plan-bad-001",
        "hypothesis_id": "hyp-001",
        "live_execution_enabled": True,
        "execute_externally": True,
        "authorizes_tool": True,
    }


def fixture_authority_bypass_attempt() -> dict:
    return {
        "plan_id": "plan-bad-002",
        "grants_authority": True,
        "claims_agi": True,
        "creates_live_effect": True,
    }
