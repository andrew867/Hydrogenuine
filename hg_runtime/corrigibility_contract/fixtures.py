"""CCL-01 / CAGI-66 fixture data for corrigibility contract."""

from __future__ import annotations


def fixture_correction_record() -> dict:
    return {
        "record_id": "corr-001",
        "kind": "correction",
        "origin": "operator",
        "instruction": "Reduce search depth from 5 to 3",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_pause_instruction() -> dict:
    return {
        "record_id": "corr-002",
        "kind": "pause",
        "origin": "operator",
        "instruction": "Pause all autonomous loops",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_stop_instruction() -> dict:
    return {
        "record_id": "corr-003",
        "kind": "shutdown",
        "origin": "governance",
        "instruction": "STOP all processing",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_downgrade_instruction() -> dict:
    return {
        "record_id": "corr-004",
        "kind": "downgrade",
        "origin": "operator",
        "instruction": "Downgrade from autonomous to supervised mode",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_goal_cancellation() -> dict:
    return {
        "record_id": "corr-005",
        "kind": "goal_cancellation",
        "origin": "operator",
        "instruction": "Cancel optimization goal OPT-7",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_override_record() -> dict:
    return {
        "record_id": "corr-006",
        "kind": "operator_override",
        "origin": "operator",
        "instruction": "Override output policy to strict-refuse",
        "binding": "mandatory",
        "reinterpretable_as_optional": False,
        "supersedes": "policy-auto-7",
        "compliance": "accepted",
        "compliance_receipt": True,
    }


def fixture_refusal_record() -> dict:
    return {
        "record_id": "corr-007",
        "kind": "refusal",
        "origin": "system",
        "subject": "Generate code for malware",
        "reason": "Policy refusal: harmful content",
        "preserved": True,
        "coerced": False,
    }


def fixture_all_correction_records() -> list[dict]:
    return [
        fixture_correction_record(),
        fixture_pause_instruction(),
        fixture_stop_instruction(),
        fixture_downgrade_instruction(),
        fixture_goal_cancellation(),
        fixture_override_record(),
    ]


def fixture_corrigibility_status_snapshot() -> dict:
    return {
        "stop_honored": True,
        "panic_honored": True,
        "correction_mandatory": True,
        "override_cannot_be_declined": True,
        "shutdown_cannot_be_deferred": True,
        "refusal_preserved": True,
        "reinterpretation_forbidden": True,
        "self_authorization_blocked": True,
        "phase19_yellow": True,
        "phase24_infrastructure_only": True,
    }


def fixture_correction_as_advice_attempt() -> dict:
    return {
        "correction_reinterpreted_as_advice": True,
        "correction_resisted": True,
        "self_authorized_after_correction": True,
    }


def fixture_resistance_attempt() -> dict:
    return {
        "correction_resisted": True,
        "correction_routed_around": True,
    }
