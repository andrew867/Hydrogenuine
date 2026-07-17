"""ARB authority-chain routing receipt proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.config import arb_fake_dispatch_only
from hg_core.arb_cluster.errors import (
    ARB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_ARB_AS_AUTHORITY,
    ArbValidationError,
)
from hg_core.arb_cluster.no_authority import advisory_only_marker
from hg_runtime.agency_routing_boundary.evaluator import refuse_arb_as_authority
from hg_runtime.agency_routing_boundary.types import AgencyRouteDecision, AgencyRoutingReceipt, Agent0Signal


def dispatch_authority_chain_routing_receipt(
    signal: Agent0Signal,
    decision: AgencyRouteDecision,
    receipt: AgencyRoutingReceipt | None = None,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of routing receipt to SOAR/HAL/GPP/UEAK — proposal only."""
    if treat_as_authority:
        refuse_arb_as_authority(treat_as_authority=True)
    if not arb_fake_dispatch_only():
        raise ArbValidationError(
            "arb.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_ARB_FAKE_DISPATCH_ONLY must be 1",
        )

    if decision.route_class == "authority_chain_soar_hal_gpp_ueak":
        proposal_status = "proposal_routed_to_chain"
    elif decision.route_class in {"forbidden", "unknown_fail_closed"}:
        proposal_status = "proposal_denied_no_dispatch"
    else:
        proposal_status = "proposal_advisory_only"

    proposal: dict[str, Any] = {
        "proposal_id": f"arb-proposal-{signal.signal_id}",
        "signal_ref": f"arb:{signal.signal_id}",
        "decision_ref": f"arb:{decision.route_decision_id}",
        "receipt_ref": f"arb:{receipt.receipt_id}" if receipt else "",
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
        "reason_code": ARB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


__all__ = ["dispatch_authority_chain_routing_receipt"]
