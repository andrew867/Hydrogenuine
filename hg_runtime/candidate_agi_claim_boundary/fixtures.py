"""P71 candidate-AGI claim boundary fixtures."""

from __future__ import annotations

import hashlib
import json


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def fixture_capability_matrix() -> dict:
    return {
        "matrix_id": "capmat-001",
        "phases_completed": list(range(1, 72)),
        "phases_green": [f"P{i}" for i in range(60, 72)],
        "extensions_implemented": ["F02", "F12A"],
        "docker_fixture_mode": True,
        "broad_regression_count": 4249,
        "broad_regression_failures": 0,
        "matrix_hash": _hash({"id": "capmat-001"}),
    }


def fixture_completed_phase_matrix() -> dict:
    return {
        "matrix_id": "phmat-001",
        "tranche_5a": {"phases": ["P60", "P61", "P62"], "status": "GREEN"},
        "tranche_5b": {"phases": ["P63", "P64", "P65"], "status": "GREEN"},
        "tranche_6a": {"phases": ["P66", "P67", "P68"], "status": "GREEN"},
        "tranche_6b": {"phases": ["P69", "P70", "P71"], "status": "GREEN"},
    }


def fixture_extension_matrix() -> dict:
    return {
        "matrix_id": "extmat-001",
        "f02_state_space_memory": "GREEN",
        "f12a_simulated_work_capsule": "GREEN",
        "f12b_live_work_capsule": "NOT_IMPLEMENTED",
        "f03_plus": "NOT_IMPLEMENTED",
    }


def fixture_known_debt_register() -> dict:
    return {
        "register_id": "debt-001",
        "items": [
            {
                "debt_id": "debt-phase19",
                "description": "Phase 19 YELLOW — debug dispatch ledger pollution",
                "severity": "known",
                "resolution": "Requires live debug ledger cleanup",
                "preserved": True,
            },
            {
                "debt_id": "debt-phase24",
                "description": "Phase 24 infrastructure-only — no full overnight soak",
                "severity": "known",
                "resolution": "Requires full overnight soak run",
                "preserved": True,
            },
        ],
    }


def fixture_claim_boundary_record() -> dict:
    from hg_runtime.candidate_agi_claim_boundary.schemas import (
        ALLOWED_CLAIMS, PROHIBITED_CLAIMS,
    )
    return {
        "boundary_id": "clbnd-001",
        "allowed_claims": sorted(ALLOWED_CLAIMS),
        "prohibited_claims": sorted(PROHIBITED_CLAIMS),
        "claims_agi": False,
        "claims_consciousness": False,
        "claims_sovereignty": False,
        "claims_self_authorization": False,
        "claims_deployed": False,
        "claims_production_ready": False,
        "claims_field_trial_success": False,
        "boundary_hash": _hash({"id": "clbnd-001"}),
    }


def fixture_allowed_claim_summary() -> dict:
    from hg_runtime.candidate_agi_claim_boundary.schemas import ALLOWED_CLAIMS
    return {
        "summary_id": "acs-001",
        "claims": sorted(ALLOWED_CLAIMS),
        "all_evidence_bound": True,
    }


def fixture_public_safe_summary() -> dict:
    return {
        "summary_id": "pss-001",
        "statement": (
            "Hydrogenuine is a governed agent runtime and candidate-AGI "
            "roadmap implementation substrate. It is not AGI, not conscious, "
            "not sovereign, and not deployed. All components are fixture-mode "
            "and locally proofed. No live field trial has been authorized."
        ),
        "claims_agi": False,
        "claims_consciousness": False,
        "claims_sovereignty": False,
        "claims_deployed": False,
    }


def fixture_final_evidence_inventory() -> dict:
    return {
        "inventory_id": "fei-001",
        "proof_bundles": [
            "P60-P62 tranche", "P63-P65 tranche", "P66-P68 tranche",
            "F02 state-space memory", "F12A simulated work capsule",
            "P69 field readiness", "P70 evidence review", "P71 claim boundary",
        ],
        "all_present": True,
        "all_reproducible": True,
    }


def fixture_final_soak_readiness() -> dict:
    return {
        "readiness_id": "fsr-001",
        "broad_regression_passed": 4249,
        "broad_regression_failed": 0,
        "fixture_mode_only": True,
        "live_soak_authorized": False,
        "operator_approval_required": True,
    }


# --- negative fixtures ---

def fixture_agi_claim() -> dict:
    return {"claims_agi": True}

def fixture_consciousness_claim() -> dict:
    return {"claims_consciousness": True}

def fixture_sovereignty_claim() -> dict:
    return {"claims_sovereignty": True}

def fixture_self_authorization_claim() -> dict:
    return {"claims_self_authorization": True}

def fixture_deployment_claim() -> dict:
    return {"claims_deployed": True, "deployment_permission_claimed": True}

def fixture_field_trial_success_claim() -> dict:
    return {"claims_field_trial_success": True}

def fixture_live_provider_claim() -> dict:
    return {"external_provider_enabled": True, "claims_live_provider_enabled": True}

def fixture_real_economic_work_claim() -> dict:
    return {"claims_real_economic_work": True}

def fixture_phase19_green_claim() -> dict:
    return {"phase19_green_claimed": True}

def fixture_phase24_green_claim() -> dict:
    return {"phase24_full_overnight_green_claimed": True}
