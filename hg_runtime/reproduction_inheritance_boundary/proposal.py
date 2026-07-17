"""RIB authority-chain child creation proposal — slice 4, fake dispatch only."""

from __future__ import annotations

from typing import Any

from hg_core.rib_cluster.config import rib_fake_dispatch_only
from hg_core.rib_cluster.errors import (
    RIB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
    REFUSED_BOOTSTRAP_AS_PERMISSION,
    RibValidationError,
)
from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.router import refuse_rib_as_authority
from hg_runtime.reproduction_inheritance_boundary.types import ChildBootstrapPacket, SpawnRequest


def dispatch_authority_chain_child_proposal(
    spawn_request: SpawnRequest,
    bootstrap_packet: ChildBootstrapPacket,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Fake dispatch of child creation proposal to authority chain — proposal only."""
    if treat_as_authority:
        refuse_rib_as_authority(treat_as_authority=True)
    if not rib_fake_dispatch_only():
        raise RibValidationError(
            "rib.refused.live_dispatch",
            "live authority-chain dispatch is disabled; HG_RIB_FAKE_DISPATCH_ONLY must be 1",
        )
    proposal: dict[str, Any] = {
        "proposal_id": f"rib-proposal-{spawn_request.spawn_request_id}",
        "spawn_request_ref": f"rib:{spawn_request.spawn_request_id}",
        "bootstrap_packet_ref": f"rib:{bootstrap_packet.bootstrap_packet_id}",
        "proposal_status": "proposal_advisory_only",
        "authority_chain_ref": "fixture:soar-hal-gpp-ueak",
        "dispatch_mode": "fake_only",
        "permit_minted": False,
        "execution_admitted": False,
        "child_authority_created": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "live_spawn": False,
    }
    return {
        **advisory_only_marker(),
        "status": "dispatched",
        "reason_code": RIB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED,
        "proposal": proposal,
        "fake_dispatch_only": True,
        "permission_granted": False,
        "child_authority_created": False,
        "external_action_taken": False,
    }


def refuse_bootstrap_packet_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RibValidationError(
            REFUSED_BOOTSTRAP_AS_PERMISSION,
            "bootstrap packet is not permission",
        )


__all__ = [
    "dispatch_authority_chain_child_proposal",
    "refuse_bootstrap_packet_as_permission",
]
