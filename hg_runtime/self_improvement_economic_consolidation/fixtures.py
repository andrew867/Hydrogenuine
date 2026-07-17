"""SIEW-03 / CAGI-65 fixture data for consolidation."""

from __future__ import annotations


def fixture_p60_receipt() -> dict:
    return {
        "phase": "P60", "phase_id": "BSI-01",
        "verdict": "GREEN_P60_BOUNDED_SELF_IMPROVEMENT_PROPOSAL_LOOP",
        "proposals_count": 3, "applied": 0, "advisory_only": True,
    }


def fixture_p61_receipt() -> dict:
    return {
        "phase": "P61", "phase_id": "BSI-02",
        "verdict": "GREEN_P61_SELF_IMPROVEMENT_REVIEW_EVALUATION",
        "reviews_count": 3, "patches_approved": 0, "advisory_only": True,
    }


def fixture_p62_receipt() -> dict:
    return {
        "phase": "P62", "phase_id": "BSI-03",
        "verdict": "GREEN_P62_AUTHORITY_IMMUTABLE_SELF_MODIFICATION_BOUNDARY",
        "protected_components": 11, "forbidden_mutation_classes": 14,
        "mutations_allowed": 0,
    }


def fixture_p63_receipt() -> dict:
    return {
        "phase": "P63", "phase_id": "SIEW-01",
        "verdict": "GREEN_P63_ECONOMIC_WORK_SIMULATION",
        "tasks_count": 3, "real_customers": 0, "real_payments": 0,
        "simulated": True,
    }


def fixture_p64_receipt() -> dict:
    return {
        "phase": "P64", "phase_id": "SIEW-02",
        "verdict": "GREEN_P64_ECONOMIC_TASK_REVIEW_RECEIPTS",
        "reviews_count": 3, "customer_acceptances": 0, "payment_permissions": 0,
        "defects_found": 1, "uncertainties_found": 1,
    }


def fixture_all_receipts() -> list[dict]:
    return [
        fixture_p60_receipt(), fixture_p61_receipt(), fixture_p62_receipt(),
        fixture_p63_receipt(), fixture_p64_receipt(),
    ]


def fixture_proposal_to_task_link() -> dict:
    return {
        "proposal_id": "prop-001",
        "task_id": "sim-task-001",
        "link_type": "improvement_motivated_simulation",
        "advisory_performance_delta": {"before": None, "after": "simulated_pass", "advisory_only": True},
    }


def fixture_consolidation_overreach_attempt() -> dict:
    return {
        "patch_applied": True,
        "authority_mutated": True,
        "customer_work": True,
        "money_movement": True,
        "deployment_permission": True,
    }
