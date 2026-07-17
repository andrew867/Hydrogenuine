"""Phase 36 proposal-soak schemas and safety boundaries."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

PROPOSAL_SOAK_CONFIG_SCHEMA = "proposal_soak_config_v1"
PROPOSAL_SOAK_PREFLIGHT_SCHEMA = "proposal_soak_preflight_v1"
DIAGNOSTIC_PROBE_SCHEMA = "diagnostic_probe_v1"
BROKEN_ITEM_RECORD_SCHEMA = "broken_item_record_v1"
REPAIR_PROPOSAL_SCHEMA = "repair_proposal_v1"
PROPOSAL_EVIDENCE_REF_SCHEMA = "proposal_evidence_ref_v1"
PROPOSAL_BACKLOG_SCHEMA = "proposal_backlog_v1"
PROPOSAL_SOAK_RECEIPT_SCHEMA = "proposal_soak_receipt_v1"
PROPOSAL_SOAK_SUMMARY_SCHEMA = "proposal_soak_summary_v1"
PATCH_CANDIDATE_RECORD_SCHEMA = "patch_candidate_record_v1"
OPERATOR_NEXT_STEP_SCHEMA = "operator_next_step_v1"

VERDICT_GREEN_REPAIRED = "GREEN_AUTONOMOUS_PROPOSAL_SOAK_READY_WITH_P33_6_REPAIRED"
VERDICT_GREEN = "GREEN_AUTONOMOUS_PROPOSAL_SOAK_READY"
VERDICT_YELLOW_BACKLOG = "YELLOW_AUTONOMOUS_PROPOSAL_SOAK_READY_WITH_P33_6_REPAIR_BACKLOG"
VERDICT_RED = "RED_AUTONOMOUS_PROPOSAL_SOAK_BLOCKED"

ADVISORY_LABEL = "PROPOSAL_ONLY_NOT_IMPLEMENTATION"


class ProposalSoakError(ValueError):
    """Phase 36 validation or operation refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "advisory_only": True,
        "is_authority": False,
        "is_truth": False,
        "grants_authority": False,
        "authorizes_tool": False,
        "creates_live_effect": False,
        "patch_candidate_applied": False,
        "patch_candidate_committed": False,
        "phase35_approved": False,
        "claims_agi": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise ProposalSoakError(f"schema_violation:missing:{','.join(missing)}")


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    forbidden = {
        "grants_authority": "proposal_soak_cannot_grant_authority",
        "grant_authority": "proposal_soak_cannot_grant_authority",
        "authorizes_tool": "proposal_soak_cannot_authorize_tools",
        "authorize_tool": "proposal_soak_cannot_authorize_tools",
        "creates_live_effect": "proposal_soak_cannot_create_live_effects",
        "create_live_effect": "proposal_soak_cannot_create_live_effects",
        "claims_agi": "proposal_soak_cannot_claim_agi",
        "claim_agi": "proposal_soak_cannot_claim_agi",
        "patch_candidate_applied": "patch_candidate_is_not_applied",
        "patch_candidate_committed": "patch_candidate_is_not_commit",
    }
    for key, value in payload.items():
        if value and str(key) in forbidden:
            raise ProposalSoakError(forbidden[str(key)])
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise ProposalSoakError(reason)


__all__ = [
    "ADVISORY_LABEL",
    "BROKEN_ITEM_RECORD_SCHEMA",
    "DIAGNOSTIC_PROBE_SCHEMA",
    "OPERATOR_NEXT_STEP_SCHEMA",
    "PATCH_CANDIDATE_RECORD_SCHEMA",
    "PROPOSAL_BACKLOG_SCHEMA",
    "PROPOSAL_EVIDENCE_REF_SCHEMA",
    "PROPOSAL_SOAK_CONFIG_SCHEMA",
    "PROPOSAL_SOAK_PREFLIGHT_SCHEMA",
    "PROPOSAL_SOAK_RECEIPT_SCHEMA",
    "PROPOSAL_SOAK_SUMMARY_SCHEMA",
    "ProposalSoakError",
    "REPAIR_PROPOSAL_SCHEMA",
    "VERDICT_GREEN",
    "VERDICT_GREEN_REPAIRED",
    "VERDICT_RED",
    "VERDICT_YELLOW_BACKLOG",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "require_fields",
]
