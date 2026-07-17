"""IPB authority-chain local decision proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.config import ipb_fake_dispatch_only
from hg_core.ipb_cluster.errors import (
    IPB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_IPB_AS_AUTHORITY,
    IpbValidationError,
)
from hg_core.ipb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_power_boundary.evaluator import refuse_ipb_as_authority
from hg_runtime.internal_power_boundary.types import InternalDecision


def dispatch_local_decision_proposal(
    decision: InternalDecision,
    evaluation: dict[str, object],
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of local decision proposal to HAL/GPP/UEAK chain — proposal only."""
    if treat_as_authority:
        refuse_ipb_as_authority(treat_as_authority=True)
    if not ipb_fake_dispatch_only():
        raise IpbValidationError(
            "ipb.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_IPB_FAKE_DISPATCH_ONLY must be 1",
        )
    status = str(evaluation.get("status", "unknown"))
    band = evaluation.get("band", 0)
    if status == "escalation_required" and decision.decision_class == "authority_chain_escalation":
        proposal_status = "proposal_routed_to_chain"
    elif status in {"contained", "refused"} or band == 4:
        proposal_status = "proposal_denied_no_dispatch"
    elif status == "recorded" and int(band) <= 1:
        proposal_status = "proposal_advisory_local_only"
    else:
        proposal_status = "proposal_advisory_only"

    proposal: dict[str, Any] = {
        "proposal_id": f"ipb-proposal-{decision.decision_id}",
        "decision_ref": f"ipb:{decision.decision_id}",
        "evaluation_status": status,
        "band": band,
        "proposal_status": proposal_status,
        "authority_chain_ref": "fixture:soar-hal-gpp-ueak",
        "dispatch_mode": "fake_only",
        "permit_minted": False,
        "execution_admitted": False,
        "oea_ter_called": False,
        "permission_granted": False,
    }
    return {
        **advisory_only_marker(),
        "status": "dispatched",
        "reason_code": IPB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


def refuse_ipb_proposal_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise IpbValidationError(
            REFUSED_IPB_AS_AUTHORITY,
            "local decision proposal is not permission",
        )


__all__ = [
    "dispatch_local_decision_proposal",
    "refuse_ipb_proposal_as_permission",
]
