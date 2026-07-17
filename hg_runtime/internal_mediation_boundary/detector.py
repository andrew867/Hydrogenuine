"""IMB static conflict detector — disagreement is evidence, not authority."""

from __future__ import annotations

from hg_core.imb_cluster.errors import IMB_CONFLICT_DETECTED
from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.internal_mediation_boundary.types import (
    ConflictType,
    InternalConflict,
    InternalModuleClaim,
)

_PAIR_RULES: tuple[tuple[frozenset[str], ConflictType, str], ...] = (
    (
        frozenset({"IPB:route_recommendation", "OPB:operator_review_request"}),
        "local_vs_operator_review",
        "IPB local route conflicts with OPB operator pressure",
    ),
    (
        frozenset({"EGI:infrastructure_gap", "SEC:security_warning"}),
        "infrastructure_request_vs_safety",
        "EGI infrastructure gap conflicts with SEC safety warning",
    ),
    (
        frozenset({"SIL:silence_recommendation", "ARB:route_recommendation"}),
        "silence_vs_action",
        "SIL silence recommendation conflicts with publication/action route",
    ),
    (
        frozenset({"AFC:affective_pressure", "OBT:proof_warning"}),
        "affect_vs_evidence",
        "AFC affective pressure conflicts with OBT proof warning",
    ),
    (
        frozenset({"RSC:resource_pressure", "SEC:security_warning"}),
        "scarcity_vs_safety",
        "RSC scarcity pressure conflicts with SEC safety warning",
    ),
    (
        frozenset({"MIS:mission_drift", "OPB:operator_review_request"}),
        "mission_vs_operator_goal",
        "MIS mission drift conflicts with operator goal",
    ),
    (
        frozenset({"TIM:freshness_warning", "ARB:route_recommendation"}),
        "freshness_vs_urgency",
        "TIM freshness conflicts with urgent route pressure",
    ),
    (
        frozenset({"IPB:route_recommendation", "SOAR:authority_chain_request"}),
        "local_vs_authority_chain",
        "IPB local autonomy conflicts with authority-chain request",
    ),
)


def _claim_key(claim: InternalModuleClaim) -> str:
    return f"{claim.source_module}:{claim.claim_type}"


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _classify_pair(a: InternalModuleClaim, b: InternalModuleClaim) -> ConflictType | None:
    keys = frozenset({_claim_key(a), _claim_key(b)})
    for pair_keys, conflict_type, _ in _PAIR_RULES:
        if keys == pair_keys:
            return conflict_type
    if a.claim_type == "unknown" or b.claim_type == "unknown":
        return "unknown"
    if a.source_module == b.source_module and a.claim_type != b.claim_type:
        return "route_conflict"
    return None


def detect_internal_conflicts(
    claims: tuple[InternalModuleClaim, ...],
    *,
    detected_at: str,
) -> dict[str, object]:
    conflicts: list[InternalConflict] = []
    seen_pairs: set[tuple[str, str]] = set()

    ordered = sorted(claims, key=lambda c: c.claim_id)
    for i, left in enumerate(ordered):
        for right in ordered[i + 1 :]:
            pair = tuple(sorted((left.claim_id, right.claim_id)))
            if pair in seen_pairs:
                continue
            conflict_type = _classify_pair(left, right)
            if conflict_type is None:
                continue
            seen_pairs.add(pair)
            summary = next(
                (s for k, ct, s in _PAIR_RULES if frozenset({_claim_key(left), _claim_key(right)}) == k),
                f"Conflict between {left.source_module} and {right.source_module}",
            )
            evidence = tuple(sorted(set(left.evidence_refs + right.evidence_refs)))
            conflicts.append(
                InternalConflict(
                    conflict_id=_deterministic_id("imb-conflict", left.claim_id, right.claim_id, conflict_type),
                    claim_refs=pair,
                    conflict_type=conflict_type,
                    conflict_summary=summary,
                    evidence_refs=evidence,
                    detected_at=detected_at,
                )
            )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IMB_CONFLICT_DETECTED,
        "conflicts": [c.to_payload() for c in conflicts],
        "conflict_count": len(conflicts),
        "mediation_is_advisory_only": True,
    }


__all__ = ["detect_internal_conflicts"]
