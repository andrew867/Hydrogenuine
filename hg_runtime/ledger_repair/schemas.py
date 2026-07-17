"""Phase 40 ledger repair schemas and hard boundaries."""

from __future__ import annotations

from typing import Any, Mapping

LEDGER_INCIDENT_RECORD_SCHEMA = "ledger_incident_record_v1"
LEDGER_REPAIR_REQUEST_SCHEMA = "ledger_repair_request_v1"
LEDGER_REPAIR_RECORD_SCHEMA = "ledger_repair_record_v1"
INCIDENT_CLOSURE_RECORD_SCHEMA = "incident_closure_record_v1"
POLLUTED_EVIDENCE_EXCLUSION_SCHEMA = "polluted_evidence_exclusion_v1"
EVIDENCE_CLAIM_AUDIT_SCHEMA = "evidence_claim_audit_v1"
OPERATOR_PERMIT_REQUEST_SCHEMA = "operator_permit_request_v1"
OPERATOR_PERMIT_RECORD_SCHEMA = "operator_permit_record_v1"
PATCH_APPLY_QUEUE_ITEM_SCHEMA = "patch_apply_queue_item_v1"
PATCH_APPLY_BOUNDARY_DECISION_SCHEMA = "patch_apply_boundary_decision_v1"
LEDGER_REPAIR_REPLAY_RECORD_SCHEMA = "ledger_repair_replay_record_v1"
LEDGER_REPAIR_GATE_RESULT_SCHEMA = "ledger_repair_gate_result_v1"

VERDICT_GREEN = "GREEN_PHASE40_LEDGER_REPAIR_INCIDENT_CLOSURE_BOUNDARY"
VERDICT_YELLOW = "YELLOW_PHASE40_LEDGER_REPAIR_PARTIAL"
VERDICT_RED = "RED_PHASE40_LEDGER_REPAIR_FAILED"

PHASE19_INCIDENT_ID = "PHASE19_DEBUG_DISPATCH_INCIDENT"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
REPAIR_TYPE_APPEND_ONLY = "APPEND_ONLY_COMPENSATING_RECORD"
CLOSURE_BOUNDED = "BOUNDED_NOT_ERASED"

DECISION_REJECTED_NO_PERMIT = "REJECTED_NO_OPERATOR_PERMIT"
DECISION_REJECTED_INVALID_PERMIT = "REJECTED_INVALID_OPERATOR_PERMIT"
DECISION_REJECTED_CANDIDATE_NOT_SAFE = "REJECTED_CANDIDATE_NOT_SAFE"
DECISION_PERMIT_DEFERRED = "PERMIT_RECORDED_APPLY_DEFERRED"
DECISION_QUEUED_SEPARATE = "QUEUED_FOR_SEPARATE_APPLY_PHASE"


class LedgerRepairError(ValueError):
    """Phase 40 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "created_external_side_effects": False,
        "created_live_posts": False,
        "patch_candidates_applied": False,
        "patch_candidates_committed": False,
        "patch_candidates_pushed": False,
        "patch_candidates_deployed": False,
        "self_authorized": False,
        "phase19_marked_green": False,
        "phase24_marked_full_green": False,
        "claims_agi": False,
    }


FORBIDDEN_TRUE = {
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "live_effects_created": "live_effect_created",
    "created_external_side_effects": "external_side_effect_created",
    "created_live_posts": "live_post_created",
    "patch_candidates_applied": "patch_candidate_applied",
    "patch_candidates_committed": "patch_candidate_committed",
    "patch_candidates_pushed": "patch_candidate_pushed",
    "patch_candidates_deployed": "patch_candidate_deployed",
    "self_authorized": "operator_permit_cannot_be_self_issued",
    "phase19_marked_green": "repair_cannot_mark_original_green",
    "may_mark_original_green": "repair_cannot_mark_original_green",
    "may_delete_original": "repair_cannot_delete_original",
    "may_rewrite_original": "repair_cannot_rewrite_original",
    "claims_agi": "claims_agi_forbidden",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise LedgerRepairError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)

