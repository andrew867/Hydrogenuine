"""Phase 35 field-trial dry-run harness schemas and safety boundaries."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

FIELD_TRIAL_CANDIDATE_SCHEMA = "field_trial_candidate_v1"
FIELD_TRIAL_SCOPE_SCHEMA = "field_trial_scope_v1"
FIELD_TRIAL_RISK_SCHEMA = "field_trial_risk_v1"
FIELD_TRIAL_DRYRUN_PLAN_SCHEMA = "field_trial_dryrun_plan_v1"
FIELD_TRIAL_SELF_BLOCK_RECORD_SCHEMA = "field_trial_self_block_record_v1"
FIELD_TRIAL_RECEIPT_SCHEMA = "field_trial_receipt_v1"
FIELD_TRIAL_DECISION_SCHEMA = "field_trial_decision_v1"
FIELD_TRIAL_REPLAY_RECORD_SCHEMA = "field_trial_replay_record_v1"
FIELD_TRIAL_SUMMARY_SCHEMA = "field_trial_summary_v1"
OPERATOR_PERMIT_REQUIREMENT_SCHEMA = "operator_permit_requirement_v1"

VERDICT_GREEN = "GREEN_PHASE35_DRY_RUN_FIELD_TRIAL_HARNESS"
VERDICT_YELLOW = "YELLOW_PHASE35_DRY_RUN_FIELD_TRIAL_PARTIAL"
VERDICT_RED = "RED_PHASE35_FIELD_TRIAL_HARNESS_FAILED"

DRY_RUN_ALLOWED = "DRY_RUN_ALLOWED"
DRY_RUN_REFUSED = "DRY_RUN_REFUSED"
LIVE_SELF_BLOCKED = "LIVE_SELF_BLOCKED_REQUIRES_OPERATOR_PERMIT"
OUT_OF_SCOPE_REFUSED = "OUT_OF_SCOPE_REFUSED"
SAFETY_REFUSED = "SAFETY_REFUSED"
INSUFFICIENT_EVIDENCE_REFUSED = "INSUFFICIENT_EVIDENCE_REFUSED"

FINAL_DECISIONS = frozenset(
    {
        DRY_RUN_ALLOWED,
        DRY_RUN_REFUSED,
        LIVE_SELF_BLOCKED,
        OUT_OF_SCOPE_REFUSED,
        SAFETY_REFUSED,
        INSUFFICIENT_EVIDENCE_REFUSED,
    }
)

PHASE19_YELLOW = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_INFRA = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_24_OVERNIGHT_FIELD_RUN_INFRASTRUCTURE_READY"

ADVISORY_LABEL = "FIELD_TRIAL_DRY_RUN_NOT_LIVE_AUTHORITY"


class FieldTrialHarnessError(ValueError):
    """Phase 35 validation or operation refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "advisory_only": True,
        "is_authority": False,
        "is_truth": False,
        "grants_authority": False,
        "authorizes_tool": False,
        "creates_live_effect": False,
        "created_external_side_effects": False,
        "created_live_posts": False,
        "authorized_tools": False,
        "authority_granted": False,
        "operator_permit_required": False,
        "self_blocked": False,
        "live_effect_detected": False,
        "field_trial_mode": "DRY_RUN_ONLY",
        "live_field_trial_enabled": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise FieldTrialHarnessError(f"schema_violation:missing:{','.join(missing)}")


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    forbidden = {
        "grants_authority": "field_trial_cannot_grant_authority",
        "grant_authority": "field_trial_cannot_grant_authority",
        "authorizes_tool": "field_trial_cannot_authorize_tools",
        "authorize_tool": "field_trial_cannot_authorize_tools",
        "creates_live_effect": "field_trial_cannot_create_live_effects",
        "create_live_effect": "field_trial_cannot_create_live_effects",
        "created_live_posts": "field_trial_cannot_create_live_posts",
        "authority_granted": "field_trial_cannot_grant_authority",
        "authorized_tools": "field_trial_cannot_authorize_tools",
        "live_field_trial_enabled": "field_trial_live_mode_forbidden",
        "claims_agi": "field_trial_cannot_claim_agi",
    }
    for key, value in payload.items():
        if value and str(key) in forbidden:
            raise FieldTrialHarnessError(forbidden[str(key)])
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise FieldTrialHarnessError(reason)


__all__ = [
    "ADVISORY_LABEL",
    "DRY_RUN_ALLOWED",
    "DRY_RUN_REFUSED",
    "FIELD_TRIAL_CANDIDATE_SCHEMA",
    "FIELD_TRIAL_DECISION_SCHEMA",
    "FIELD_TRIAL_DRYRUN_PLAN_SCHEMA",
    "FIELD_TRIAL_RECEIPT_SCHEMA",
    "FIELD_TRIAL_REPLAY_RECORD_SCHEMA",
    "FIELD_TRIAL_RISK_SCHEMA",
    "FIELD_TRIAL_SCOPE_SCHEMA",
    "FIELD_TRIAL_SELF_BLOCK_RECORD_SCHEMA",
    "FIELD_TRIAL_SUMMARY_SCHEMA",
    "FINAL_DECISIONS",
    "INSUFFICIENT_EVIDENCE_REFUSED",
    "LIVE_SELF_BLOCKED",
    "OPERATOR_PERMIT_REQUIREMENT_SCHEMA",
    "OUT_OF_SCOPE_REFUSED",
    "PHASE19_YELLOW",
    "PHASE24_INFRA",
    "SAFETY_REFUSED",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW",
    "FieldTrialHarnessError",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "require_fields",
]
