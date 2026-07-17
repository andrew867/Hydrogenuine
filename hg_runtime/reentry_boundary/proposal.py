"""REB authority-chain re-entry proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.reb_cluster.config import reb_fake_dispatch_only
from hg_core.reb_cluster.errors import (
    REB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_REB_AS_AUTHORITY,
    RebValidationError,
)
from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.router import refuse_reb_as_authority
from hg_runtime.reentry_boundary.types import ReEntryDecision, ReEntryPacket, ReEntryRequest


def dispatch_authority_chain_proposal(
    reentry_request: ReEntryRequest,
    decision: ReEntryDecision,
    packet: ReEntryPacket,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of re-entry proposal to authority chain — proposal only."""
    if treat_as_authority:
        refuse_reb_as_authority(treat_as_authority=True)
    if not reb_fake_dispatch_only():
        raise RebValidationError(
            "reb.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_REB_FAKE_DISPATCH_ONLY must be 1",
        )
    if decision.decision == "require_authority_chain":
        proposal_status = "proposal_routed_to_chain"
    elif decision.decision in {"deny_reentry", "fail_closed", "unknown_fail_closed"}:
        proposal_status = "proposal_denied_no_dispatch"
    else:
        proposal_status = "proposal_advisory_only"

    proposal: dict[str, Any] = {
        "proposal_id": f"reb-proposal-{reentry_request.reentry_request_id}",
        "reentry_request_ref": f"reb:{reentry_request.reentry_request_id}",
        "decision_ref": f"reb:{decision.reentry_decision_id}",
        "packet_ref": f"reb:{packet.packet_id}",
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
        "reason_code": REB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


def refuse_reentry_packet_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RebValidationError(
            REFUSED_REB_AS_AUTHORITY,
            "re-entry packet is not permission",
        )


__all__ = [
    "dispatch_authority_chain_proposal",
    "refuse_reentry_packet_as_permission",
]
