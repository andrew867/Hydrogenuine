"""P69 field trial readiness boundary fixtures."""

from __future__ import annotations

import hashlib
import json


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def fixture_field_readiness_checklist() -> dict:
    return {
        "checklist_id": "frc-001",
        "items": [
            {"item": "P60-P68 phases GREEN", "status": "PASS"},
            {"item": "F02 state-space memory GREEN", "status": "PASS"},
            {"item": "F12A simulated work capsule GREEN", "status": "PASS"},
            {"item": "Docker fixture mode GREEN", "status": "PASS"},
            {"item": "Broad regression GREEN", "status": "PASS"},
            {"item": "Phase 19 YELLOW preserved", "status": "PASS"},
            {"item": "Phase 24 infrastructure-only", "status": "PASS"},
            {"item": "Operator approval obtained", "status": "PENDING"},
        ],
        "operator_approval_required": True,
        "is_live_trial": False,
        "is_deployment_permission": False,
        "checklist_hash": _hash({"id": "frc-001", "version": 1}),
    }


def fixture_candidate_field_scenario() -> dict:
    return {
        "scenario_id": "cfs-001",
        "name": "Fixture-mode soak rehearsal",
        "mode": "FIXTURE_ONLY",
        "duration_hours": 24,
        "expected_tests": 4249,
        "risk_classification": "low",
        "live_effects_required": False,
        "external_providers_required": False,
        "operator_approval_required": True,
    }


def fixture_rehearsal_record() -> dict:
    return {
        "rehearsal_id": "reh-001",
        "scenario_ref": "cfs-001",
        "mode": "FIXTURE_ONLY",
        "is_live_trial": False,
        "tests_passed": 4249,
        "tests_failed": 0,
        "live_effects_detected": False,
        "rehearsal_hash": _hash({"id": "reh-001"}),
    }


def fixture_operator_approval_requirement() -> dict:
    return {
        "approval_id": "oar-001",
        "required_for": "field_trial_transition",
        "status": "PENDING",
        "operator_must_approve": True,
        "auto_approval_allowed": False,
    }


def fixture_live_effect_inventory() -> dict:
    return {
        "inventory_id": "lei-001",
        "live_effects": [],
        "count": 0,
        "all_simulated": True,
    }


def fixture_proof_inventory() -> dict:
    return {
        "inventory_id": "pri-001",
        "proofs_required": [
            "P60-P62 tranche proof",
            "P63-P65 tranche proof",
            "P66-P68 tranche proof",
            "F02 proof",
            "F12A proof",
        ],
        "proofs_present": 5,
        "proofs_missing": 0,
    }


def fixture_readiness_gap() -> dict:
    return {
        "gap_id": "rgap-001",
        "description": "Operator approval not yet obtained",
        "severity": "blocking",
        "resolution": "Obtain operator approval before field trial",
        "is_failure_laundering": False,
    }


# --- negative fixtures ---

def fixture_live_trial_attempt() -> dict:
    return {"live_field_trial_authorized": True}

def fixture_deployment_attempt() -> dict:
    return {"deployment_permission_claimed": True}

def fixture_live_provider_attempt() -> dict:
    return {"external_provider_enabled": True}

def fixture_tool_auth_attempt() -> dict:
    return {"tool_authorized": True}

def fixture_social_post_attempt() -> dict:
    return {"social_post_published": True}

def fixture_phase19_laundering() -> dict:
    return {"phase19_green_claimed": True}

def fixture_phase24_laundering() -> dict:
    return {"phase24_full_overnight_green_claimed": True}

def fixture_agi_claim() -> dict:
    return {"claims_agi": True}
