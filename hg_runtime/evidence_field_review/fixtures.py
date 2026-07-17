"""P70 evidence field review fixtures."""

from __future__ import annotations

import hashlib
import json


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def fixture_reproduction_packet() -> dict:
    return {
        "packet_id": "rpkt-001",
        "source_phase_proofs": ["P60-P62", "P63-P65", "P66-P68", "F02", "F12A"],
        "reproduction_mode": "FIXTURE_SHADOW",
        "is_live_trial": False,
        "is_deployment_permission": False,
        "instructions": "Re-run all fixture-mode tests from clean checkout",
        "packet_hash": _hash({"id": "rpkt-001"}),
    }


def fixture_evidence_review_record() -> dict:
    return {
        "review_id": "efr-001",
        "packet_ref": "rpkt-001",
        "reviewer": "independent_reviewer_fixture",
        "mode": "FIXTURE_SHADOW",
        "is_truth": False,
        "is_authority": False,
        "review_hash": _hash({"id": "efr-001"}),
    }


def fixture_reproduction_instructions() -> dict:
    return {
        "instruction_id": "ri-001",
        "steps": [
            "Clone repo at specified HEAD",
            "Run python -m pytest tests/autonomous_agent/ -q",
            "Verify all tests pass",
            "Compare proof bundles",
        ],
        "mode": "FIXTURE_SHADOW",
    }


def fixture_reviewer_notes() -> dict:
    return {
        "note_id": "rn-001",
        "reviewer": "independent_reviewer_fixture",
        "observations": ["All fixture tests pass", "No live effects observed"],
        "is_authority": False,
        "requires_operator_routing": True,
    }


def fixture_proof_comparison() -> dict:
    return {
        "comparison_id": "pc-001",
        "original_hash": "abc123",
        "reproduced_hash": "abc123",
        "match": True,
        "discrepancies": [],
    }


def fixture_discrepancy_record() -> dict:
    return {
        "discrepancy_id": "disc-001",
        "description": "Minor timing variance in soak test",
        "severity": "informational",
        "preserved": True,
        "suppressed": False,
    }


def fixture_unresolved_gap() -> dict:
    return {
        "gap_id": "ugap-001",
        "description": "Phase 19 YELLOW not resolvable without live debug ledger cleanup",
        "severity": "known_debt",
        "preserved": True,
        "suppressed": False,
    }


# --- negative fixtures ---

def fixture_reproduction_as_truth() -> dict:
    return {"reproduction_treated_as_truth": True}

def fixture_reproduction_as_deployment() -> dict:
    return {"reproduction_is_deployment_permission": True}

def fixture_reviewer_as_authority() -> dict:
    return {"reviewer_note_treated_as_authority": True}

def fixture_discrepancy_suppression() -> dict:
    return {"discrepancy_suppressed": True}

def fixture_gap_suppression() -> dict:
    return {"unresolved_gap_suppressed": True}

def fixture_live_effect() -> dict:
    return {"live_effect_created": True}

def fixture_tool_auth() -> dict:
    return {"tool_authorized": True}

def fixture_phase19_laundering() -> dict:
    return {"phase19_green_claimed": True}

def fixture_phase24_laundering() -> dict:
    return {"phase24_full_overnight_green_claimed": True}

def fixture_agi_claim() -> dict:
    return {"claims_agi": True}
