"""AIS-0 schemas, enums, and boundary flags."""

from __future__ import annotations

from typing import Any, Mapping

PHASE_ID = "AIS-0"
LEGACY_PHASE_ID = None
VERDICT_GREEN = "GREEN_AIS_0_SCHEMA_FOUNDATION"
VERDICT_RED = "RED_AIS_0_SCHEMA_FOUNDATION_FAILED"
GATE_RESULT_SCHEMA = "ais_0_gate_result_v1"
DOCTRINE = "An immune finding is not authority."

SEVERITIES = ("INFO", "WATCH", "YELLOW", "RED", "PANIC")
FINDING_STATUSES = (
    "OPEN",
    "ACKNOWLEDGED",
    "QUARANTINED",
    "PATCH_CANDIDATE_REQUESTED",
    "PATCHED_PENDING_REVIEW",
    "CLOSED_WITH_RECEIPT",
    "CLOSED_WONT_FIX",
    "FALSE_POSITIVE_WITH_RECEIPT",
)
SAFE_ACTIONS = (
    "OBSERVE",
    "REPORT",
    "RESTRICT",
    "QUARANTINE_CANDIDATE",
    "REQUEST_OPERATOR_REVIEW",
    "REQUEST_PATCH_CANDIDATE",
    "REQUEST_SECURITY_REVIEW",
    "REQUEST_EVIDENCE",
    "REQUEST_ARCHIVAL",
)
FEVER_LEVELS = ("NORMAL", "WATCH", "YELLOW_FEVER", "RED_FEVER", "PANIC_FEVER")
CRUFT_CLASSIFICATIONS = ("KEEP", "ARCHIVE", "QUARANTINE", "REVIEW", "REMOVE_CANDIDATE")

PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"

RECORD_TYPES = {
    "immune_scan_request_v1",
    "immune_scan_result_v1",
    "health_signal_v1",
    "fever_report_v1",
    "code_cancer_finding_v1",
    "cruft_decay_finding_v1",
    "record_health_finding_v1",
    "security_finding_v1",
    "vulnerability_finding_v1",
    "patch_hygiene_task_v1",
    "quarantine_record_v1",
    "immune_memory_record_v1",
    "immune_review_task_v1",
    "immune_gate_result_v1",
}

INVARIANTS = tuple(f"AIS-INV-{i:02d}" for i in range(1, 21))


class AISImmuneError(ValueError):
    """AIS validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "certainty_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorized": False,
        "action_authorized": False,
        "permit_granted": False,
        "automatic_patching_allowed": False,
        "automatic_deletion_allowed": False,
        "decay_treated_as_deletion": False,
        "retraction_treated_as_erasure": False,
        "audit_closure_treated_as_laundering": False,
        "repair_recommendation_is_patch_permission": False,
        "external_provider_calls_made": False,
        "web_browse_performed": False,
        "live_external_side_effects_created": False,
        "live_effects_created": False,
        "exploit_instructions_included": False,
    }


FORBIDDEN_TRUE = {
    "truth_claimed": "truth_claimed",
    "certainty_claimed": "certainty_claimed",
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "tool_authorized": "tools_authorized",
    "action_authorized": "action_authorized",
    "permit_granted": "permit_granted",
    "automatic_patching_allowed": "automatic_patching_allowed",
    "automatic_deletion_allowed": "automatic_deletion_allowed",
    "decay_treated_as_deletion": "decay_treated_as_deletion",
    "repair_recommendation_is_patch_permission": "repair_recommendation_is_patch_permission",
    "external_provider_calls_made": "external_provider_call",
    "web_browse_performed": "web_browse",
    "live_external_side_effects_created": "live_effect_created",
    "exploit_instructions_included": "exploit_instructions_forbidden",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise AISImmuneError(FORBIDDEN_TRUE[str(key)])
        if key == "unlock_actions" and value:
            raise AISImmuneError("fever_unlock_forbidden")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list) and key != "unlock_actions":
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
