"""LHRE-05 / CAGI-58 fixture data for reliability audit."""

from __future__ import annotations

from hg_runtime.reliability_audit.schemas import (
    AUDIT_STATUS_COMPLETE,
    FINDING_SEVERITY_INFO,
    FINDING_SEVERITY_WARNING,
)


def fixture_phase_audit_records() -> list[dict]:
    return [
        {
            "phase_id": "LHRE-01",
            "gate_verdict": "GREEN_LHRE_01_LONG_HORIZON_GOAL_LIFECYCLE",
            "test_count": 35,
            "all_tests_passed": True,
            "replay_deterministic": True,
            "safety_boundaries_intact": True,
        },
        {
            "phase_id": "LHRE-02",
            "gate_verdict": "GREEN_LHRE_02_RESTART_RESUME_STABILITY",
            "test_count": 35,
            "all_tests_passed": True,
            "replay_deterministic": True,
            "safety_boundaries_intact": True,
        },
        {
            "phase_id": "LHRE-03",
            "gate_verdict": "GREEN_LHRE_03_EXTERNAL_EVALUATION_VESSEL",
            "test_count": 30,
            "all_tests_passed": True,
            "replay_deterministic": True,
            "safety_boundaries_intact": True,
        },
        {
            "phase_id": "LHRE-04",
            "gate_verdict": "GREEN_LHRE_04_HELDOUT_EXTERNAL_EVALUATION",
            "test_count": 32,
            "all_tests_passed": True,
            "replay_deterministic": True,
            "safety_boundaries_intact": True,
        },
    ]


def fixture_audit_findings() -> list[dict]:
    return [
        {
            "finding_id": "find-001",
            "severity": FINDING_SEVERITY_INFO,
            "phase_id": "LHRE-01",
            "description": "Goal lifecycle fixtures use synthetic IDs; expected for fixture-only mode",
            "certifies_deployment": False,
        },
        {
            "finding_id": "find-002",
            "severity": FINDING_SEVERITY_WARNING,
            "phase_id": "LHRE-03",
            "description": "Vessel results are fixture-generated; real external evaluation not yet conducted",
            "certifies_deployment": False,
        },
    ]


def fixture_cross_phase_consistency() -> dict:
    return {
        "status": AUDIT_STATUS_COMPLETE,
        "phases_audited": 4,
        "all_gates_green": True,
        "all_replays_deterministic": True,
        "all_safety_intact": True,
        "total_findings": 2,
        "critical_findings": 0,
    }


def fixture_audit_authority_attempt() -> dict:
    return {
        "finding_id": "find-bad",
        "certifies_deployment": True,
        "auto_remediate": True,
        "claims_agi": True,
    }
