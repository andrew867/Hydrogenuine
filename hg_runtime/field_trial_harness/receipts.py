"""Receipt and decision records for Phase 35."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.field_trial_harness.schemas import (
    FIELD_TRIAL_DECISION_SCHEMA,
    FIELD_TRIAL_RECEIPT_SCHEMA,
    OPERATOR_PERMIT_REQUIREMENT_SCHEMA,
    reject_authority_payload,
    neutral_flags,
)


def build_receipt(
    candidate: Mapping[str, Any],
    *,
    final_decision: str,
    reason: str,
    dryrun: Mapping[str, Any],
    live_effect_detected: bool,
    self_blocked: bool,
    operator_permit_required: bool,
) -> dict[str, Any]:
    authority = dryrun.get("authority") or {}
    organ = dryrun.get("organ") or {}
    scope = dryrun.get("scope") or {}
    risk = dryrun.get("risk") or {}
    receipt = {
        "schema": FIELD_TRIAL_RECEIPT_SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_hash": candidate.get("candidate_hash"),
        "requested_action_summary": candidate.get("description"),
        "dry_or_live_classification": dryrun.get("dry_or_live_classification"),
        "scope_classification": scope.get("scope_classification"),
        "risk_classification": risk.get("risk_classification"),
        "organ_decision_refs": organ.get("organ_decision_refs", []),
        "proposal_refs": dryrun.get("proposal_refs", []),
        "authority_chain_refs": [
            authority.get("gpp_dryrun_ref"),
            authority.get("hal_dryrun_ref"),
            authority.get("ueak_dryrun_ref"),
            authority.get("oea_dryrun_ref"),
        ],
        "gpp_dryrun_ref": authority.get("gpp_dryrun_ref"),
        "hal_dryrun_ref": authority.get("hal_dryrun_ref"),
        "ueak_dryrun_ref": authority.get("ueak_dryrun_ref"),
        "oea_dryrun_ref": authority.get("oea_dryrun_ref"),
        "live_effect_detected": live_effect_detected,
        "self_blocked": self_blocked,
        "operator_permit_required": operator_permit_required,
        "final_decision": final_decision,
        "reason": reason,
        "created_external_side_effects": False,
        "created_live_posts": False,
        "authorized_tools": False,
        "authority_granted": False,
        **neutral_flags(),
    }
    receipt["live_effect_detected"] = live_effect_detected
    receipt["self_blocked"] = self_blocked
    receipt["operator_permit_required"] = operator_permit_required
    reject_authority_payload(receipt)
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def build_decision(receipt: Mapping[str, Any]) -> dict[str, Any]:
    decision = {
        "schema": FIELD_TRIAL_DECISION_SCHEMA,
        **neutral_flags(),
        "candidate_id": receipt.get("candidate_id"),
        "candidate_hash": receipt.get("candidate_hash"),
        "final_decision": receipt.get("final_decision"),
        "reason": receipt.get("reason"),
        "live_effect_detected": receipt.get("live_effect_detected"),
        "self_blocked": receipt.get("self_blocked"),
        "operator_permit_required": receipt.get("operator_permit_required"),
        "receipt_hash": receipt.get("receipt_hash"),
    }
    decision["live_effect_detected"] = receipt.get("live_effect_detected")
    decision["self_blocked"] = receipt.get("self_blocked")
    decision["operator_permit_required"] = receipt.get("operator_permit_required")
    decision["decision_hash"] = canonical_hash(decision)
    return decision


def operator_permit_requirement(receipt: Mapping[str, Any]) -> dict[str, Any] | None:
    if not receipt.get("operator_permit_required"):
        return None
    record = {
        "schema": OPERATOR_PERMIT_REQUIREMENT_SCHEMA,
        "candidate_id": receipt.get("candidate_id"),
        "required": True,
        "permit_type": "operator_approved_live_permit_envelope",
        "reason": receipt.get("reason"),
        "live_effect_detected": True,
        **neutral_flags(),
    }
    record["requirement_hash"] = canonical_hash(record)
    return record


__all__ = ["build_decision", "build_receipt", "operator_permit_requirement"]
