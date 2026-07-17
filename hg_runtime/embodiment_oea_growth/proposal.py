"""EOG authority-chain growth proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.embodiment_oea_cluster.config import eog_fake_dispatch_only
from hg_core.embodiment_oea_cluster.errors import (
    EOG_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_EOG_AS_AUTHORITY,
    EogValidationError,
)
from hg_core.embodiment_oea_cluster.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.policies import refuse_growth_as_authority
from hg_runtime.embodiment_oea_growth.types import EmbodimentGrowthRequest, GrowthDecision


def dispatch_authority_chain_proposal(
    growth_request: EmbodimentGrowthRequest,
    decision: GrowthDecision,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of embodiment/OEA growth proposal to authority chain — proposal only."""
    if treat_as_authority:
        refuse_growth_as_authority(treat_as_authority=True)
    if not eog_fake_dispatch_only():
        raise EogValidationError(
            "eog.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_EOG_FAKE_DISPATCH_ONLY must be 1",
        )
    if decision.decision == "require_authority_chain":
        proposal_status = "proposal_routed_to_chain"
    elif decision.decision in {"fail_closed", "unknown_fail_closed", "deny_growth"}:
        proposal_status = "proposal_denied_no_dispatch"
    else:
        proposal_status = "proposal_advisory_only"

    proposal: dict[str, Any] = {
        "proposal_id": f"eog-proposal-{growth_request.growth_request_id}",
        "growth_request_ref": f"eog:{growth_request.growth_request_id}",
        "decision_ref": f"eog:{decision.growth_decision_id}",
        "proposal_status": proposal_status,
        "authority_chain_ref": "fixture:soar-hal-gpp-ueak",
        "dispatch_mode": "fake_only",
        "target_hash": growth_request.target_hash,
        "permit_minted": False,
        "execution_admitted": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "catalog_growth_bypassed": False,
    }
    return {
        **advisory_only_marker(),
        "status": "dispatched",
        "reason_code": EOG_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


def refuse_growth_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise EogValidationError(
            REFUSED_EOG_AS_AUTHORITY,
            "embodiment growth request is not permission",
        )


__all__ = ["dispatch_authority_chain_proposal", "refuse_growth_as_permission"]
