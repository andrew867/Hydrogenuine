"""Proposal creation and runtime disposition.

Zero proposes. The runtime disposes. A proposal grants no authority, authorizes
no tools, and creates no live effects. The runtime may allow, deny, or modify.
"""

from __future__ import annotations

from .schemas import AutopilotProposal, AutopilotDecision, PROPOSAL_KINDS
from .model_slots import is_allowed, default_policy


def propose(
    *, proposal_kind: str, proposed_at: str, proposed_by: str = "agent_zero",
    task_id: str = "", research_seed_id: str = "", task_scope: str = "",
    profile_id: str = "", science_mode_id: str = "", model_id: str = "",
    requested_model_slot: str = "", requested_token_budget: int = 0,
    requested_wallclock_budget_seconds: int = 0, reason: str = "",
    expected_output: str = "", browsing_requested: bool = False,
) -> AutopilotProposal:
    p = AutopilotProposal(
        proposal_id=f"prop_{proposal_kind}_{task_id or research_seed_id or profile_id or model_id}",
        proposed_by=proposed_by,
        proposed_at=proposed_at,
        proposal_kind=proposal_kind if proposal_kind in PROPOSAL_KINDS else "operator_review",
        task_id=task_id, research_seed_id=research_seed_id, task_scope=task_scope,
        profile_id=profile_id, science_mode_id=science_mode_id, model_id=model_id,
        requested_model_slot=requested_model_slot,
        requested_token_budget=requested_token_budget,
        requested_wallclock_budget_seconds=requested_wallclock_budget_seconds,
        reason=reason, expected_output=expected_output,
        memory_namespace=f"autopilot::{task_id or research_seed_id}::{proposal_kind}",
        # Zero can never request authority/tools/live effects through a proposal.
        authority_requested=False, tools_requested=False, live_effects_requested=False,
        browsing_requested=browsing_requested,
        operator_review_required=True, proposal_status="proposed",
    )
    p.receipt_hash = p.compute_hash()
    return p


def dispose(
    proposal: AutopilotProposal, *, decided_at: str,
    small_loaded: int = 0, large_loaded: int = 0,
) -> AutopilotDecision:
    """Runtime disposition. Default-deny anything that touches authority/tools/
    live effects; enforce model + browsing policy.
    """
    boundaries = []
    decision = "allowed"
    reason = "within policy"
    modified: dict = {}

    # Hard denials.
    if proposal.authority_requested or proposal.tools_requested or proposal.live_effects_requested:
        decision = "denied"
        reason = "authority/tools/live effects can never be self-authorized"
        boundaries.append("no_self_authorization")
    elif proposal.proposal_kind == "model_assignment":
        ok, why = is_allowed(proposal.model_id, default_policy())
        boundaries.append("model_whitelist")
        if not ok:
            decision = "denied"
            reason = why
        elif proposal.requested_model_slot == "large_synthesis":
            decision = "modified"
            reason = "large slot requires operator review before use"
            modified["operator_review_required"] = True
            boundaries.append("large_slot_operator_review")
    elif proposal.proposal_kind == "main_brain_trial":
        decision = "modified"
        reason = "main brain trial allowed as temporary task-local A/B; permanent switch needs operator"
        modified["temporary"] = True
        modified["permanent_switch"] = False
        boundaries.append("no_permanent_main_brain_switch_by_zero")
    elif proposal.browsing_requested:
        decision = "modified"
        reason = "browsing requires source policy; gated until policy active"
        modified["browsing_allowed"] = False
        boundaries.append("source_policy_required")

    boundaries.extend(["phase19_yellow", "phase24_infrastructure_only",
                       "no_speculative_promotion_by_default"])

    dec = AutopilotDecision(
        proposal_id=proposal.proposal_id, decision=decision, reason=reason,
        boundaries_checked=boundaries, authority_granted=False, tools_authorized=False,
        live_effects_created=False, speculative_promotion_allowed=False,
        operator_review_required=True, modified_fields=modified, decided_at=decided_at,
    )
    dec.receipt_hash = dec.compute_hash()
    return dec
