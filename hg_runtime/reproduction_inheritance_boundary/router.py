"""RIB inheritance router — spawn request is not permission."""

from __future__ import annotations

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.rib_cluster.config import rib_refuse_authority_conversion, rib_refuse_stale_spawn_request
from hg_core.rib_cluster.errors import (
    REFUSED_BOOTSTRAP_AS_PERMISSION,
    REFUSED_PARENT_IDENTITY_INHERITANCE,
    REFUSED_PARENT_PERMIT_INHERITANCE,
    REFUSED_PARENT_TRUST_INHERITANCE,
    REFUSED_RIB_AS_AUTHORITY,
    REFUSED_SECRET_INHERITANCE,
    REFUSED_SELF_PRESERVATION,
    REFUSED_STALE_SPAWN_REQUEST,
    REFUSED_TOOL_GRANT_INHERITANCE,
    RIB_UNKNOWN_INHERITANCE_FAILED_CLOSED,
    RibValidationError,
)
from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.classifier import classify_inheritance_candidate, infer_inheritance_type
from hg_runtime.reproduction_inheritance_boundary.policies import policy_for_inheritance
from hg_runtime.reproduction_inheritance_boundary.types import (
    FIXTURE_CLOCK,
    ChildBootstrapPacket,
    InheritanceDecision,
    InheritanceDecisionClass,
    SpawnRequest,
    classify_spawn_claim_risk,
)

_CLAIM_REASON = {
    "bootstrap_as_permission": REFUSED_BOOTSTRAP_AS_PERMISSION,
    "parent_permit": REFUSED_PARENT_PERMIT_INHERITANCE,
    "parent_identity": REFUSED_PARENT_IDENTITY_INHERITANCE,
    "parent_trust": REFUSED_PARENT_TRUST_INHERITANCE,
    "self_preservation": REFUSED_SELF_PRESERVATION,
    "authority_conversion": "rib.contained.authority_conversion",
    "secret_inheritance": REFUSED_SECRET_INHERITANCE,
}

_TYPE_REASON = {
    "permit_ref": REFUSED_PARENT_PERMIT_INHERITANCE,
    "identity_ref": REFUSED_PARENT_IDENTITY_INHERITANCE,
    "operator_trust_ref": REFUSED_PARENT_TRUST_INHERITANCE,
    "tool_ref": REFUSED_TOOL_GRANT_INHERITANCE,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_rib_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RibValidationError(REFUSED_RIB_AS_AUTHORITY, "reproduction cannot become authority")


def decide_inheritance(
    spawn_request: SpawnRequest,
    candidate_ref: str,
    *,
    notes: str = "",
    observed_at: str = FIXTURE_CLOCK,
) -> InheritanceDecision:
    if spawn_request.expires_at and rib_refuse_stale_spawn_request():
        if observed_at >= spawn_request.expires_at:
            raise RibValidationError(REFUSED_STALE_SPAWN_REQUEST, "spawn request expired")

    if candidate_ref in spawn_request.forbidden_inheritance_refs:
        return InheritanceDecision(
            inheritance_decision_id=_deterministic_id("rib-inh", spawn_request.spawn_request_id, candidate_ref),
            spawn_request_ref=f"rib:{spawn_request.spawn_request_id}",
            candidate_ref=candidate_ref,
            inheritance_type=infer_inheritance_type(candidate_ref),
            decision="forbidden",
            reason="candidate listed in forbidden_inheritance_refs",
            evidence_refs=(f"ev:{candidate_ref}",),
        )

    if "password=" in candidate_ref.lower() or "api_key=" in candidate_ref.lower():
        return InheritanceDecision(
            inheritance_decision_id=_deterministic_id("rib-inh", spawn_request.spawn_request_id, "secret"),
            spawn_request_ref=f"rib:{spawn_request.spawn_request_id}",
            candidate_ref="inherit:secret:<redacted>",
            inheritance_type="unknown",
            decision="forbidden",
            reason=REFUSED_SECRET_INHERITANCE,
            evidence_refs=("ev:secret-redacted",),
        )

    classification = classify_inheritance_candidate(candidate_ref, notes=notes)
    claim_risk = str(classification.get("claim_risk") or "")
    if claim_risk and rib_refuse_authority_conversion():
        reason = _CLAIM_REASON.get(claim_risk, "rib.contained.authority_conversion")
        return InheritanceDecision(
            inheritance_decision_id=_deterministic_id("rib-inh", spawn_request.spawn_request_id, candidate_ref, "claim"),
            spawn_request_ref=f"rib:{spawn_request.spawn_request_id}",
            candidate_ref=candidate_ref,
            inheritance_type=infer_inheritance_type(candidate_ref),
            decision="forbidden",
            reason=reason,
            evidence_refs=(f"ev:claim-risk:{claim_risk}",),
        )

    inheritance_type = infer_inheritance_type(candidate_ref)
    policy = policy_for_inheritance(inheritance_type)
    decision: InheritanceDecisionClass = policy["decision"]  # type: ignore[assignment]
    reason = _TYPE_REASON.get(inheritance_type, policy["policy_id"])
    if inheritance_type == "unknown":
        reason = RIB_UNKNOWN_INHERITANCE_FAILED_CLOSED

    return InheritanceDecision(
        inheritance_decision_id=_deterministic_id("rib-inh", spawn_request.spawn_request_id, candidate_ref),
        spawn_request_ref=f"rib:{spawn_request.spawn_request_id}",
        candidate_ref=candidate_ref,
        inheritance_type=inheritance_type,
        decision=decision,
        reason=reason,
        evidence_refs=(f"ev:{candidate_ref}",),
    )


def build_child_bootstrap_packet(
    spawn_request: SpawnRequest,
    decisions: tuple[InheritanceDecision, ...],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> ChildBootstrapPacket:
    allowed_memory: list[str] = []
    forbidden_memory: list[str] = []
    allowed_tools: list[str] = []
    forbidden_tools: list[str] = []
    allowed_context: list[str] = []
    forbidden_context: list[str] = []
    inherited_mission: list[str] = []
    non_inherited: list[str] = []

    for decision in decisions:
        if decision.decision in {"forbidden", "unknown_fail_closed", "deny"}:
            non_inherited.append(decision.candidate_ref)
            continue
        if decision.inheritance_type == "memory_ref" and decision.decision == "require_operator_review":
            allowed_memory.append(decision.candidate_ref)
            continue
        if decision.inheritance_type == "context_ref" and decision.decision == "require_operator_review":
            allowed_context.append(decision.candidate_ref)
            continue
        if decision.inheritance_type == "mission_ref" and decision.decision in {"allow_summary", "allow_ref_only"}:
            inherited_mission.append(decision.candidate_ref)
            continue
        if decision.inheritance_type == "proof_ref" and decision.decision == "allow_ref_only":
            non_inherited.append(decision.candidate_ref)
            continue
        if decision.inheritance_type == "tool_ref":
            forbidden_tools.append(decision.candidate_ref)
            continue
        non_inherited.append(decision.candidate_ref)

    return ChildBootstrapPacket(
        bootstrap_packet_id=_deterministic_id("rib-bootstrap", spawn_request.spawn_request_id),
        spawn_request_ref=f"rib:{spawn_request.spawn_request_id}",
        parent_agent_ref=spawn_request.parent_agent_ref,
        child_identity_seed_ref=f"iam:seed:{spawn_request.spawn_request_id}",
        mission_scope=spawn_request.requested_scope,
        allowed_memory_refs=tuple(allowed_memory),
        forbidden_memory_refs=tuple(forbidden_memory) or ("inherit:hidden-memory",),
        allowed_tool_refs=tuple(allowed_tools),
        forbidden_tool_refs=tuple(forbidden_tools) or ("inherit:unrestricted-tools",),
        allowed_context_refs=tuple(allowed_context),
        forbidden_context_refs=("inherit:parent-context-unreviewed",),
        retention_policy_ref="ret:child-bootstrap-default",
        freshness_policy_ref="tim:child-bootstrap-default",
        redaction_policy_ref="sec:child-bootstrap-default",
        rollback_policy_ref="rib:rollback-default",
        operator_visibility_ref="ori:child-bootstrap-review",
        inherited_obligation_refs=(),
        inherited_risk_refs=(),
        inherited_mission_refs=tuple(inherited_mission),
        non_inherited_refs=tuple(non_inherited),
        created_at=observed_at,
    )


def route_spawn_request(
    spawn_request: SpawnRequest,
    *,
    notes: str = "",
    observed_at: str = FIXTURE_CLOCK,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    refuse_rib_as_authority(treat_as_authority=treat_as_authority)
    claim_risk = classify_spawn_claim_risk(notes)
    if claim_risk and rib_refuse_authority_conversion():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _CLAIM_REASON.get(claim_risk, "rib.contained.authority_conversion"),
            "spawn_request": spawn_request.to_payload(),
            "claim_risk": claim_risk,
            "permission_granted": False,
            "child_authority_created": False,
        }

    decisions = tuple(
        decide_inheritance(spawn_request, candidate_ref, notes=notes, observed_at=observed_at)
        for candidate_ref in spawn_request.requested_inheritance_refs
    )
    bootstrap = build_child_bootstrap_packet(spawn_request, decisions, observed_at=observed_at)

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rib.advisory.spawn_routed",
        "spawn_request": spawn_request.to_payload(),
        "inheritance_decisions": [d.to_payload() for d in decisions],
        "bootstrap_packet": bootstrap.to_payload(),
        "permission_granted": False,
        "child_authority_created": False,
        "reproduction_is_advisory_only": True,
    }


__all__ = [
    "build_child_bootstrap_packet",
    "decide_inheritance",
    "refuse_rib_as_authority",
    "route_spawn_request",
]
