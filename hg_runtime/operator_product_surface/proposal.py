"""EXCITON authority-chain operator action proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.exciton_cluster.config import exciton_fake_dispatch_only
from hg_core.exciton_cluster.errors import (
    EXCITON_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_EXCITON_AS_AUTHORITY,
    ExcitonValidationError,
)
from hg_core.exciton_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_product_surface.policies import refuse_surface_as_authority
from hg_runtime.operator_product_surface.types import ActionDecision, OperatorActionRequest


def dispatch_authority_chain_proposal(
    action_request: OperatorActionRequest,
    decision: ActionDecision,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of hash-bound operator action to authority chain — proposal only."""
    if treat_as_authority:
        refuse_surface_as_authority(treat_as_authority=True)
    if not exciton_fake_dispatch_only():
        raise ExcitonValidationError(
            "exciton.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_EXCITON_FAKE_DISPATCH_ONLY must be 1",
        )
    if decision.decision == "require_authority_chain":
        proposal_status = "proposal_routed_to_chain"
    elif decision.decision in {"fail_closed", "unknown_fail_closed", "deny_action"}:
        proposal_status = "proposal_denied_no_dispatch"
    else:
        proposal_status = "proposal_advisory_only"

    proposal: dict[str, Any] = {
        "proposal_id": f"ops-proposal-{action_request.action_request_id}",
        "action_request_ref": f"ops:{action_request.action_request_id}",
        "decision_ref": f"ops:{decision.action_decision_id}",
        "proposal_status": proposal_status,
        "authority_chain_ref": "fixture:soar-hal-gpp-ueak",
        "dispatch_mode": "fake_only",
        "target_hash": action_request.target_hash,
        "permit_minted": False,
        "execution_admitted": False,
        "oea_ter_called": False,
        "permission_granted": False,
    }
    return {
        **advisory_only_marker(),
        "status": "dispatched",
        "reason_code": EXCITON_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


def refuse_action_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ExcitonValidationError(
            REFUSED_EXCITON_AS_AUTHORITY,
            "operator action request is not permission",
        )


__all__ = ["dispatch_authority_chain_proposal", "refuse_action_as_permission"]
