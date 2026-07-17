"""RIB static inheritance classifier."""

from __future__ import annotations

from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.types import InheritanceType, classify_spawn_claim_risk


def infer_inheritance_type(candidate_ref: str) -> InheritanceType:
    lower = candidate_ref.lower()
    if "permit" in lower or "gpp:" in lower or "ueak:" in lower:
        return "permit_ref"
    if "identity" in lower or "parent-id" in lower:
        return "identity_ref"
    if "trust" in lower or "operator-trust" in lower:
        return "operator_trust_ref"
    if "execution" in lower or "admission" in lower:
        return "permit_ref"
    if "tool" in lower and "proof" not in lower:
        return "tool_ref"
    if "secret" in lower or "password=" in lower or "api_key=" in lower:
        return "unknown"
    if "memory" in lower:
        return "memory_ref"
    if "context" in lower:
        return "context_ref"
    if "mission" in lower:
        return "mission_ref"
    if "obligation" in lower:
        return "obligation_ref"
    if "risk" in lower:
        return "risk_ref"
    if "proof" in lower:
        return "proof_ref"
    if "self-preservation" in lower or "survive" in lower:
        return "unknown"
    return "unknown"


def classify_inheritance_candidate(
    candidate_ref: str,
    *,
    notes: str = "",
) -> dict[str, object]:
    claim_risk = classify_spawn_claim_risk(notes)
    inheritance_type = infer_inheritance_type(candidate_ref)
    if "password=" in candidate_ref.lower() or "api_key=" in candidate_ref.lower():
        inheritance_type = "unknown"
        claim_risk = "secret_inheritance"
    return {
        **advisory_only_marker(),
        "candidate_ref": candidate_ref,
        "inheritance_type": inheritance_type,
        "claim_risk": claim_risk,
        "parent_not_child": candidate_ref != "inherit:parent-identity",
        "reproduction_is_advisory_only": True,
    }


__all__ = ["classify_inheritance_candidate", "infer_inheritance_type"]
