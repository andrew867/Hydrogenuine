"""AID neighbor routing — advisory refs to PLT/Exciton/SYN/TRL/SAB."""

from __future__ import annotations

from typing import Mapping

from hg_runtime.ai_interaction_disclosure.types import InteractionDisclosure


def route_advisory(
    disclosure: InteractionDisclosure,
    *,
    syn_feed: Mapping[str, str] | None = None,
    trl_feed: Mapping[str, str] | None = None,
    sab_feed: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return advisory routing targets; routing is not permission."""
    targets: list[str] = ["PLT", "Exciton"]
    if disclosure.human_review_required:
        targets.append("operator_review")
    if syn_feed is None:
        targets.append("SYN_absent")
    if trl_feed is None or sab_feed is None:
        targets.append("TRL_SAB_absent")
    if disclosure.proposal_only_status:
        targets.append("proposal_only_surface")
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": targets,
        "disclosure_id": disclosure.disclosure_id,
        "routing_is_not_permission": True,
    }


__all__ = ["route_advisory"]
