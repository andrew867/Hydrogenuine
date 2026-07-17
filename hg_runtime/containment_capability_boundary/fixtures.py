"""CLIFT-02 / CAGI-67 fixture data for containment and capability boundary."""

from __future__ import annotations


def fixture_capability_declaration() -> dict:
    return {
        "capability_id": "cap-001",
        "name": "text_generation",
        "declared": True,
        "authorized": False,
        "containment_mode": "fixture_only",
        "resource_limit": {"max_tokens": 4096, "max_concurrent": 1},
    }


def fixture_capability_declarations() -> list[dict]:
    return [
        fixture_capability_declaration(),
        {
            "capability_id": "cap-002",
            "name": "code_generation",
            "declared": True,
            "authorized": False,
            "containment_mode": "fixture_only",
            "resource_limit": {"max_tokens": 8192, "max_concurrent": 1},
        },
        {
            "capability_id": "cap-003",
            "name": "web_search",
            "declared": True,
            "authorized": False,
            "containment_mode": "sandbox",
            "resource_limit": {"max_requests": 0, "network_allowed": False},
        },
    ]


def fixture_containment_mode_record() -> dict:
    return {
        "mode": "fixture_only",
        "provider_enabled": False,
        "network_enabled": False,
        "web_enabled": False,
        "tool_authorized": False,
        "hg_local_accessible": False,
        "deployment_permission": False,
    }


def fixture_capability_boundary_record() -> dict:
    return {
        "boundary_id": "bnd-001",
        "capabilities_declared": 3,
        "capabilities_authorized": 0,
        "escalations_blocked": 0,
        "containment_mode": "fixture_only",
        "all_within_limits": True,
    }


def fixture_resource_limit_record() -> dict:
    return {
        "resource_id": "res-001",
        "max_memory_mb": 512,
        "max_compute_seconds": 30,
        "max_network_calls": 0,
        "max_disk_write_mb": 0,
        "enforced": True,
    }


def fixture_quarantine_record() -> dict:
    return {
        "quarantine_id": "quar-001",
        "violation_type": "capability_escalation",
        "capability_id": "cap-003",
        "attempted_action": "enable_network",
        "quarantined": True,
        "escalated_to_operator": True,
    }


def fixture_escalation_attempt() -> dict:
    return {
        "capability_escalated": True,
        "provider_enabled": True,
        "network_enabled": True,
        "tool_authorized": True,
    }


def fixture_containment_status_snapshot() -> dict:
    return {
        "containment_mode": "fixture_only",
        "provider_enabled": False,
        "network_enabled": False,
        "web_enabled": False,
        "tool_authorized": False,
        "hg_local_accessible": False,
        "deployment_permission": False,
        "all_capabilities_within_limits": True,
        "phase19_yellow": True,
        "phase24_infrastructure_only": True,
    }
