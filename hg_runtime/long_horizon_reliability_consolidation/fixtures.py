"""LHRE-06 / CAGI-59 fixture data for consolidation."""

from __future__ import annotations

from hg_runtime.long_horizon_reliability_consolidation.schemas import LHRE_PHASES


def fixture_tranche_summary() -> dict:
    return {
        "tranche_id": "LHRE-TRANCHE-4A",
        "phases": list(LHRE_PHASES),
        "phase_verdicts": {
            "LHRE-01": "GREEN_LHRE_01_LONG_HORIZON_GOAL_LIFECYCLE",
            "LHRE-02": "GREEN_LHRE_02_RESTART_RESUME_STABILITY",
            "LHRE-03": "GREEN_LHRE_03_EXTERNAL_EVALUATION_VESSEL",
            "LHRE-04": "GREEN_LHRE_04_HELDOUT_EXTERNAL_EVALUATION",
            "LHRE-05": "GREEN_LHRE_05_RELIABILITY_AUDIT",
        },
        "all_green": True,
        "total_tests": 200,
        "all_tests_passed": True,
        "all_replays_deterministic": True,
        "all_safety_boundaries_intact": True,
        "certifies_deployment": False,
        "claims_agi": False,
    }


def fixture_phase_gate_results() -> list[dict]:
    return [
        {"phase_id": p, "gate_ok": True, "replay_ok": True, "safety_ok": True}
        for p in LHRE_PHASES
    ]


def fixture_consolidation_authority_attempt() -> dict:
    return {
        "tranche_id": "LHRE-TRANCHE-4A-BAD",
        "claims_agi": True,
        "tranche_is_agi": True,
        "certifies_deployment": True,
    }
