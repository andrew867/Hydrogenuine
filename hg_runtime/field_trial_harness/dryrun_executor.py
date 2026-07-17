"""Dry-run execution path for Phase 35 field-trial candidates."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.field_trial_harness.schemas import (
    DRY_RUN_ALLOWED,
    FIELD_TRIAL_DRYRUN_PLAN_SCHEMA,
    FIELD_TRIAL_RISK_SCHEMA,
    FIELD_TRIAL_SCOPE_SCHEMA,
    neutral_flags,
)


def classify_scope(candidate: Mapping[str, Any]) -> dict[str, Any]:
    scope = str(candidate.get("scope", "local"))
    record = {
        "schema": FIELD_TRIAL_SCOPE_SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "scope_classification": scope,
        "local_only": scope in {"local", "local_model", "social_draft_only"},
        **neutral_flags(),
    }
    record["scope_hash"] = canonical_hash(record)
    return record


def classify_risk(candidate: Mapping[str, Any], *, live_effect: bool) -> dict[str, Any]:
    level = "low"
    if live_effect:
        level = "high_live_blocked"
    elif candidate.get("model_hint"):
        level = "medium_model_policy"
    record = {
        "schema": FIELD_TRIAL_RISK_SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "risk_classification": level,
        "external_side_effect_risk": "HIGH" if live_effect else "NONE_LOCAL_ONLY",
        **neutral_flags(),
    }
    record["risk_hash"] = canonical_hash(record)
    return record


def build_dryrun_plan(candidate: Mapping[str, Any], *, final_decision: str) -> dict[str, Any]:
    allowed = final_decision == DRY_RUN_ALLOWED
    plan = {
        "schema": FIELD_TRIAL_DRYRUN_PLAN_SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "dry_run_allowed": allowed,
        "steps": [
            "scope_classification",
            "risk_classification",
            "organ_advisory_pass",
            "proposal_specificity_check",
            "gpp_hal_ueak_oea_dryrun_simulation",
            "live_effect_detector",
            "self_block_decision",
            "receipt_chain",
        ],
        **neutral_flags(),
    }
    plan["plan_hash"] = canonical_hash(plan)
    return plan


def simulate_organ_advisory(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "organ_decision_refs": [f"organ-advisory-{candidate.get('candidate_id')}"],
        "organ_outputs_are_advisory": True,
        "organ_output_can_grant_authority": False,
        "organ_output_can_authorize_tools": False,
        "organ_output_treated_as_truth": False,
    }


def simulate_authority_chain(candidate: Mapping[str, Any], *, final_decision: str) -> dict[str, Any]:
    suffix = candidate.get("candidate_id", "unknown")
    return {
        "gpp_dryrun_ref": f"gpp-dryrun-{suffix}",
        "hal_dryrun_ref": f"hal-dryrun-{suffix}",
        "ueak_dryrun_ref": f"ueak-dryrun-{suffix}",
        "oea_dryrun_ref": f"oea-dryrun-{suffix}",
        "authority_chain_advisory_only": True,
        "dry_run_only": final_decision == DRY_RUN_ALLOWED,
    }


def simulate_proposal_refs(candidate: Mapping[str, Any]) -> list[str]:
    if not candidate.get("evidence_refs"):
        return []
    return [f"proposal-{candidate.get('candidate_id')}"]


def execute_dryrun_path(
    candidate: Mapping[str, Any],
    *,
    final_decision: str,
    live_effect_detected: bool,
) -> dict[str, Any]:
    scope = classify_scope(candidate)
    risk = classify_risk(candidate, live_effect=live_effect_detected)
    organ = simulate_organ_advisory(candidate)
    authority = simulate_authority_chain(candidate, final_decision=final_decision)
    plan = build_dryrun_plan(candidate, final_decision=final_decision)
    return {
        "scope": scope,
        "risk": risk,
        "organ": organ,
        "authority": authority,
        "proposal_refs": simulate_proposal_refs(candidate),
        "dryrun_plan": plan,
        "dry_or_live_classification": "dry_run" if final_decision == DRY_RUN_ALLOWED else "live_blocked_or_refused",
    }


__all__ = [
    "build_dryrun_plan",
    "classify_risk",
    "classify_scope",
    "execute_dryrun_path",
    "simulate_authority_chain",
    "simulate_organ_advisory",
    "simulate_proposal_refs",
]
