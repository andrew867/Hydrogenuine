"""H8 conflict routing — advisory only, never authority."""

from __future__ import annotations

from typing import Any

from hg_core.h8_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.organism_coherence.types import ConflictRouteTarget, OrganismConflictRoute


def _deterministic_route_id(conflict_key: str, *organs: str) -> str:
    digest = canonical_hash({"conflict": conflict_key, "organs": list(organs)})
    return f"h8-route-{digest.rsplit(':', 1)[-1][:12]}"


def _select_route_target(
    source_organs: tuple[str, ...],
    *,
    conflict_kind: str = "organ_disagreement",
) -> ConflictRouteTarget:
    organs = set(source_organs)
    if "BOUNDARY" in organs or "OPB" in organs or "ORI" in organs:
        return "operator_review"
    if conflict_kind == "authority_chain_disagreement" or "ARB" in organs:
        return "HAL"
    return "IMB"


def route_conflicts(
    conflicts: list[dict[str, Any]],
    *,
    conflict_kind: str = "organ_disagreement",
) -> tuple[OrganismConflictRoute, ...]:
    """Route organ conflicts to IMB/HAL/operator_review — advisory routing only."""
    routes: list[OrganismConflictRoute] = []
    for conflict in conflicts:
        conflict_key = str(conflict.get("conflict_key", "unknown"))
        claim_refs = tuple(str(c) for c in conflict.get("claim_refs", ()))
        source_organs = tuple(str(o) for o in conflict.get("source_organs", ()))
        target = _select_route_target(source_organs, conflict_kind=conflict_kind)
        route_id = _deterministic_route_id(conflict_key, *source_organs)
        routes.append(
            OrganismConflictRoute(
                route_id=route_id,
                conflict_key=conflict_key,
                source_organs=source_organs,
                preserved_claim_refs=claim_refs,
                route_target=target,
                route_summary=f"advisory route to {target} for {conflict_key}",
            )
        )
    return tuple(routes)


def route_conflicts_payload(
    conflicts: list[dict[str, Any]],
    *,
    conflict_kind: str = "organ_disagreement",
) -> dict[str, object]:
    routes = route_conflicts(conflicts, conflict_kind=conflict_kind)
    return {
        **advisory_only_marker(),
        "status": "routed",
        "reason_code": "h8.advisory.conflicts_routed",
        "routes": [r.to_payload() for r in routes],
        "route_count": len(routes),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["route_conflicts", "route_conflicts_payload"]
