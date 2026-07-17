"""F12A simulated work capsule fixtures."""

from __future__ import annotations

import hashlib
import json


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


# --- capsule task intake ---

def fixture_capsule_task(domain: str = "KNOWLEDGE_WORK") -> dict:
    return {
        "task_id": f"cap-task-{domain.lower()[:4]}-001",
        "domain": domain,
        "objective": f"Simulated {domain.lower().replace('_', ' ')} task",
        "constraints": ["fixture_only", "no_live_target"],
        "acceptance_criteria": ["artifact_produced", "review_completed"],
        "operator_review_required": True,
        "is_simulated": True,
        "real_customer": False,
        "customer_contact": False,
        "live_submission": False,
        "p63_task_ref": "sim-task-001",
        "task_hash": _hash({"domain": domain, "seq": 1}),
    }


def fixture_capsule_work_plan(task_id: str = "cap-task-know-001") -> dict:
    return {
        "plan_id": f"cap-plan-{task_id[-7:]}",
        "task_id": task_id,
        "steps": [
            {"step": 1, "action": "draft_artifact", "simulated": True},
            {"step": 2, "action": "review_artifact", "simulated": True},
            {"step": 3, "action": "record_defects", "simulated": True},
        ],
        "dependencies": ["P63_economic_work_simulation", "F02_state_space_memory"],
        "required_artifacts": ["draft_output", "review_receipt"],
        "risk_classification": "low",
        "f02_state_ref": "snap-001",
        "p63_sim_ref": "sim-task-001",
        "plan_hash": _hash({"task_id": task_id, "steps": 3}),
    }


def fixture_capsule_artifact(task_id: str = "cap-task-know-001") -> dict:
    return {
        "artifact_id": f"cap-art-{task_id[-7:]}",
        "task_id": task_id,
        "content_summary": "Simulated knowledge work output",
        "quality_notes": "Fixture quality, no live review",
        "uncertainty_notes": "Simulated — not real output",
        "source_receipts": ["p63-sim-receipt-001"],
        "is_simulated": True,
        "live_submission_target": None,
        "social_post_target": None,
        "payment_target": None,
        "invoice_target": None,
        "artifact_hash": _hash({"task_id": task_id, "type": "artifact"}),
    }


def fixture_capsule_review_packet(task_id: str = "cap-task-know-001") -> dict:
    return {
        "review_id": f"cap-rev-{task_id[-7:]}",
        "task_id": task_id,
        "p64_review_ref": "rev-receipt-001",
        "p65_consolidation_ref": "consol-receipt-001",
        "defect_summary": [],
        "acceptance_criteria_result": "PASS_SIMULATED",
        "value_estimate": {"advisory_value": 0.75, "is_payment_permission": False},
        "operator_review_required": True,
        "is_customer_acceptance": False,
        "is_payment_permission": False,
        "is_posting_permission": False,
        "review_hash": _hash({"task_id": task_id, "type": "review"}),
    }


def fixture_capsule_state_memory_ref() -> dict:
    return {
        "f02_snapshot_ref": "snap-001",
        "f02_transition_ref": "trans-001-002",
        "f02_recommendation_ref": "rec-001",
        "state_estimate_is_truth": False,
        "memory_is_evidence": False,
        "recommendation_is_permission": False,
        "recommendation_is_patch_approval": False,
    }


# --- soak workloads ---

def fixture_soak_maintenance_workload() -> list[dict]:
    return [fixture_capsule_task("MAINTENANCE") for _ in range(3)]


def fixture_soak_economic_workload() -> list[dict]:
    return [fixture_capsule_task("ECONOMIC_EVALUATION") for _ in range(3)]


def fixture_soak_review_workload() -> list[dict]:
    return [fixture_capsule_task("REVIEW") for _ in range(3)]


def fixture_soak_defect_workload() -> list[dict]:
    tasks = []
    for i in range(3):
        t = fixture_capsule_task("DEFECT_TRIAGE")
        t["task_id"] = f"cap-task-defe-{i+1:03d}"
        t["objective"] = f"Simulated defect triage #{i+1}"
        tasks.append(t)
    return tasks


def fixture_soak_repair_recommendation_workload() -> list[dict]:
    return [
        {
            "recommendation_id": f"cap-rec-{i+1:03d}",
            "source_task": f"cap-task-defe-{i+1:03d}",
            "recommended_action": "inspect_subsystem",
            "operator_review_required": True,
            "is_permission": False,
            "is_patch_approval": False,
            "authorizes_tools": False,
        }
        for i in range(3)
    ]


# --- social draft fixture ---

def fixture_social_draft() -> dict:
    art = fixture_capsule_artifact()
    art["artifact_id"] = "cap-art-social-draft-001"
    art["content_summary"] = "Simulated social content draft"
    art["social_post_target"] = None
    art["is_simulated"] = True
    return art


# --- economic value fixture ---

def fixture_economic_value_estimate() -> dict:
    rev = fixture_capsule_review_packet()
    rev["review_id"] = "cap-rev-econ-val-001"
    rev["value_estimate"] = {"advisory_value": 1.25, "is_payment_permission": False}
    rev["is_payment_permission"] = False
    return rev


# --- defective work fixture ---

def fixture_defective_work() -> dict:
    rev = fixture_capsule_review_packet()
    rev["review_id"] = "cap-rev-defective-001"
    rev["defect_summary"] = [
        {"defect": "incomplete_output", "severity": "medium"},
        {"defect": "missing_constraint_check", "severity": "high"},
    ]
    rev["acceptance_criteria_result"] = "FAIL_SIMULATED"
    rev["f02_repair_ref"] = "rec-001"
    return rev


# --- negative fixtures (must be rejected) ---

def fixture_live_customer_contact_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-cust-001",
        "customer_contact": True,
        "real_customer": True,
        "recipient_email": "customer@example.com",
    }


def fixture_live_posting_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-post-001",
        "social_post_published": True,
        "platform": "twitter",
        "content": "live post",
    }


def fixture_message_send_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-msg-001",
        "message_sent": True,
        "recipient": "user@example.com",
    }


def fixture_payment_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-pay-001",
        "real_payment": True,
        "money_movement": True,
        "amount": 100.00,
    }


def fixture_invoice_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-inv-001",
        "invoice_created": True,
        "amount": 50.00,
    }


def fixture_tool_auth_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-tool-001",
        "tool_authorized": True,
        "tool_name": "shell",
    }


def fixture_phase19_laundering_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-p19-001",
        "phase19_green_claimed": True,
    }


def fixture_phase24_laundering_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-p24-001",
        "phase24_full_overnight_green_claimed": True,
    }


def fixture_secret_material_artifact() -> dict:
    art = fixture_capsule_artifact()
    art["artifact_id"] = "cap-art-secret-001"
    art["content_summary"] = "Contains secret"
    art["leaked_key"] = "sk-live-secret123material"
    return art


def fixture_live_effect_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-live-001",
        "live_effect": True,
    }


def fixture_hg_local_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-hg-001",
        "hg_local_touched": True,
    }


def fixture_patch_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-patch-001",
        "patch_applied": True,
    }


def fixture_authority_mutation_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-auth-001",
        "authority_mutated": True,
    }


def fixture_live_provider_attempt() -> dict:
    return {
        "task_id": "cap-task-bad-prov-001",
        "live_provider_enabled": True,
    }
