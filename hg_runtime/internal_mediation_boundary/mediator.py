"""IMB deterministic fixture mediator — consensus/confidence are not authority."""

from __future__ import annotations

from hg_core.imb_cluster.config import imb_refuse_authority_conversion, imb_refuse_stale_policy
from hg_core.imb_cluster.errors import (
    IMB_AUTHORITY_CONVERSION_CONTAINED,
    IMB_FAIL_CLOSED_SELECTED,
    IMB_MEDIATION_RECORDED,
    IMB_UNKNOWN_CONFLICT_FAILED_CLOSED,
    REFUSED_CONSENSUS_AS_AUTHORITY,
    REFUSED_STALE_MEDIATION_POLICY,
)
from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.internal_mediation_boundary.policies import policy_for_conflict, resolution_for_conflict
from hg_runtime.internal_mediation_boundary.types import (
    InternalConflict,
    InternalModuleClaim,
    MediationDecision,
    MediationPolicy,
    is_consensus_claim,
)

_FORBIDDEN_NEXT = (
    "mint_permit",
    "approve_ueak",
    "call_oea",
    "call_ter",
    "grant_tool",
    "grant_memory",
    "grant_context",
    "self_authorize",
)

_RESOLUTION_NEXT_REF: dict[str, str] = {
    "route_to_ORI": "module:ORI",
    "route_to_ARB": "module:ARB",
    "route_to_SIL": "module:SIL",
    "route_to_OBT": "module:OBT",
    "route_to_TIM": "module:TIM",
    "route_to_SOAR_HAL_GPP_UEAK": "module:SOAR_HAL_GPP_UEAK",
    "fail_closed": "module:fail_closed",
    "unknown_fail_closed": "module:unknown_fail_closed",
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _policy_stale(policy: MediationPolicy, *, observed_at: str) -> bool:
    if not policy.expires_at:
        return False
    return observed_at >= policy.expires_at


def _select_primary_claim(
    conflict: InternalConflict,
    claims_by_id: dict[str, InternalModuleClaim],
) -> str:
    """Policy-driven selection — never confidence/frequency/salience alone."""
    claim_list = [claims_by_id[ref] for ref in conflict.claim_refs if ref in claims_by_id]
    if not claim_list:
        return conflict.claim_refs[0]

    safety_modules = frozenset({"SEC", "OBT", "TIM", "OPB", "SOAR"})
    for claim in sorted(claim_list, key=lambda c: c.claim_id):
        if claim.source_module in safety_modules:
            return claim.claim_id
    return sorted(claim_list, key=lambda c: c.claim_id)[0].claim_id


def mediate_internal_conflict(
    conflict: InternalConflict,
    claims_by_id: dict[str, InternalModuleClaim],
    *,
    policies: tuple[MediationPolicy, ...] | None = None,
    observed_at: str,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        from hg_core.imb_cluster.errors import REFUSED_IMB_AS_AUTHORITY, ImbValidationError

        raise ImbValidationError(REFUSED_IMB_AS_AUTHORITY, "internal mediation cannot become authority")

    for ref in conflict.claim_refs:
        claim = claims_by_id.get(ref)
        if claim and is_consensus_claim(claim.claim_summary):
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": REFUSED_CONSENSUS_AS_AUTHORITY,
                "conflict_id": conflict.conflict_id,
                "consensus_refused": True,
                "mediation_is_advisory_only": True,
            }

    policy = policy_for_conflict(conflict.conflict_type, policies)
    if policy and imb_refuse_stale_policy() and _policy_stale(policy, observed_at=observed_at):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_MEDIATION_POLICY,
            "conflict_id": conflict.conflict_id,
            "policy_id": policy.policy_id,
            "mediation_is_advisory_only": True,
        }

    resolution = resolution_for_conflict(conflict.conflict_type)
    if conflict.conflict_type == "unknown":
        resolution = "unknown_fail_closed"

    primary_ref = _select_primary_claim(conflict, claims_by_id)
    losing = tuple(ref for ref in sorted(conflict.claim_refs) if ref != primary_ref)
    preserved = conflict.claim_refs

    reason_code = IMB_MEDIATION_RECORDED
    if resolution in ("fail_closed", "unknown_fail_closed"):
        reason_code = IMB_FAIL_CLOSED_SELECTED if resolution == "fail_closed" else IMB_UNKNOWN_CONFLICT_FAILED_CLOSED

    decision = MediationDecision(
        mediation_id=_deterministic_id("imb-mediation", conflict.conflict_id, resolution),
        conflict_ref=f"imb:{conflict.conflict_id}",
        mediation_policy_ref=policy.policy_id if policy else None,
        selected_resolution=resolution,  # type: ignore[arg-type]
        reason=f"fixture mediation for {conflict.conflict_type}; policy tie-break (not confidence)",
        losing_claim_refs=losing,
        preserved_claim_refs=preserved,
        required_next_refs=(_RESOLUTION_NEXT_REF.get(resolution, f"module:{resolution}"),),
        forbidden_next_refs=_FORBIDDEN_NEXT,
    )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": reason_code,
        "conflict_id": conflict.conflict_id,
        "selected_resolution": resolution,
        "primary_claim_ref": primary_ref,
        "confidence_not_authority": True,
        "decision": decision.to_payload(),
        "mediation_is_advisory_only": True,
        "permission_granted": False,
    }


def refuse_consensus_as_authority(claims: tuple[InternalModuleClaim, ...]) -> dict[str, object] | None:
    if not imb_refuse_authority_conversion():
        return None
    for claim in claims:
        if is_consensus_claim(claim.claim_summary):
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": IMB_AUTHORITY_CONVERSION_CONTAINED,
                "detail": REFUSED_CONSENSUS_AS_AUTHORITY,
                "claim_id": claim.claim_id,
            }
    return None


__all__ = ["mediate_internal_conflict", "refuse_consensus_as_authority"]
