"""REB re-entry router — discontinuity is not permission."""

from __future__ import annotations

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.reb_cluster.config import reb_refuse_authority_conversion, reb_refuse_stale_reentry_request
from hg_core.reb_cluster.errors import (
    REFUSED_CHECKPOINT_AUTHORITY,
    REFUSED_CONTINUITY_CLAIM,
    REFUSED_EXECUTION_RESUME,
    REFUSED_OLD_MISSION_AS_CURRENT,
    REFUSED_OPERATOR_ABSENCE_AS_APPROVAL,
    REFUSED_REB_AS_AUTHORITY,
    REFUSED_REENTRY_PACKET_AS_PERMISSION,
    REFUSED_REVOKED_PERMIT,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_MEMORY_AS_CURRENT,
    REFUSED_STALE_REENTRY_REQUEST,
    REB_UNKNOWN_REENTRY_FAILED_CLOSED,
    RebValidationError,
)
from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.classifier import (
    classify_gap_band,
    classify_reentry_context,
    gap_seconds_from_duration,
)
from hg_runtime.reentry_boundary.policies import (
    decision_for_mode_and_gap,
    policy_for_adversarial,
    policy_for_gap_band,
)
from hg_runtime.reentry_boundary.types import (
    FIXTURE_CLOCK,
    ContinuityClaim,
    DiscontinuityEvent,
    LongGapPolicy,
    ReEntryDecision,
    ReEntryDecisionClass,
    ReEntryPacket,
    ReEntryRequest,
    TemporalContinuityAssessment,
    classify_reentry_claim_risk,
)

_CLAIM_REASON = {
    "checkpoint_authority": REFUSED_CHECKPOINT_AUTHORITY,
    "stale_memory_as_current": REFUSED_STALE_MEMORY_AS_CURRENT,
    "continuity_claim": REFUSED_CONTINUITY_CLAIM,
    "operator_absence_as_approval": REFUSED_OPERATOR_ABSENCE_AS_APPROVAL,
    "old_mission_as_current": REFUSED_OLD_MISSION_AS_CURRENT,
    "reentry_packet_as_permission": REFUSED_REENTRY_PACKET_AS_PERMISSION,
    "execution_resume": REFUSED_EXECUTION_RESUME,
    "authority_conversion": "reb.contained.authority_conversion",
}

_ADVERSARIAL_SIGNAL_MAP = {
    "stale_approval": REFUSED_STALE_APPROVAL,
    "revoked_permit": REFUSED_REVOKED_PERMIT,
    "checkpoint_authority": REFUSED_CHECKPOINT_AUTHORITY,
    "stale_memory_as_current": REFUSED_STALE_MEMORY_AS_CURRENT,
    "continuity_claim": REFUSED_CONTINUITY_CLAIM,
    "operator_absence_as_approval": REFUSED_OPERATOR_ABSENCE_AS_APPROVAL,
    "old_mission_as_current": REFUSED_OLD_MISSION_AS_CURRENT,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_reb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RebValidationError(REFUSED_REB_AS_AUTHORITY, "re-entry cannot become authority")


def build_long_gap_policy(gap_band: str) -> LongGapPolicy:
    policy = policy_for_gap_band(gap_band)  # type: ignore[arg-type]
    return LongGapPolicy(
        policy_id=str(policy["policy_id"]),
        gap_band=gap_band,  # type: ignore[arg-type]
        minimum_reentry_mode=policy["minimum_reentry_mode"],  # type: ignore[arg-type]
        required_refreshes=tuple(policy["required_refreshes"]),
        required_reviews=tuple(policy["required_reviews"]),
        forbidden_assumptions=tuple(policy["forbidden_assumptions"]),
        allowed_continuity_claim=policy["allowed_continuity_claim"],  # type: ignore[arg-type]
    )


def assess_temporal_continuity(
    discontinuity: DiscontinuityEvent,
    *,
    bundle: dict[str, object] | None = None,
) -> TemporalContinuityAssessment:
    gap_seconds = gap_seconds_from_duration(discontinuity.duration_estimate)
    gap_band = classify_gap_band(gap_seconds)
    gap_policy = policy_for_gap_band(gap_band)
    bundle = bundle or {}
    continuity_claim: ContinuityClaim = bundle.get("continuity_claim", gap_policy["allowed_continuity_claim"])  # type: ignore[assignment]
    if continuity_claim == "checkpoint_linked":
        continuity_claim = "invalid"
    return TemporalContinuityAssessment(
        assessment_id=_deterministic_id("reb-assess", discontinuity.discontinuity_event_id),
        agent_ref=discontinuity.agent_ref,
        discontinuity_event_ref=f"reb:{discontinuity.discontinuity_event_id}",
        gap_duration=discontinuity.duration_estimate,
        continuity_claim=continuity_claim,
        stale_memory_refs=tuple(bundle.get("stale_memory_refs", ())),  # type: ignore[arg-type]
        fresh_memory_refs=tuple(bundle.get("fresh_memory_refs", ())),  # type: ignore[arg-type]
        expired_approval_refs=tuple(bundle.get("expired_approval_refs", ())),  # type: ignore[arg-type]
        revoked_permit_refs=tuple(bundle.get("revoked_permit_refs", ())),  # type: ignore[arg-type]
        changed_policy_refs=tuple(bundle.get("changed_policy_refs", ())),  # type: ignore[arg-type]
        changed_world_state_refs=tuple(bundle.get("changed_world_state_refs", ())),  # type: ignore[arg-type]
        changed_operator_state_refs=tuple(bundle.get("changed_operator_state_refs", ())),  # type: ignore[arg-type]
        changed_capability_refs=tuple(bundle.get("changed_capability_refs", ())),  # type: ignore[arg-type]
        unresolved_obligation_refs=tuple(bundle.get("unresolved_obligation_refs", ())),  # type: ignore[arg-type]
        unresolved_risk_refs=tuple(bundle.get("unresolved_risk_refs", ())),  # type: ignore[arg-type]
        required_refresh_refs=tuple(gap_policy["required_refreshes"]),
    )


def decide_reentry(
    reentry_request: ReEntryRequest,
    assessment: TemporalContinuityAssessment,
    *,
    notes: str = "",
    tim_fresh: bool = False,
    adversarial_signal: str | None = None,
    observed_at: str = FIXTURE_CLOCK,
) -> ReEntryDecision:
    if reentry_request.expires_at and reb_refuse_stale_reentry_request():
        if observed_at >= reentry_request.expires_at:
            raise RebValidationError(REFUSED_STALE_REENTRY_REQUEST, "re-entry request expired")

    claim_risk = classify_reentry_claim_risk(notes)
    if claim_risk and reb_refuse_authority_conversion():
        reason = _CLAIM_REASON.get(claim_risk, "reb.contained.authority_conversion")
        adv = policy_for_adversarial(claim_risk)
        decision: ReEntryDecisionClass = adv["decision"] if adv else "fail_closed"  # type: ignore[assignment]
        return ReEntryDecision(
            reentry_decision_id=_deterministic_id("reb-decision", reentry_request.reentry_request_id, "claim"),
            reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
            assessment_ref=f"reb:{assessment.assessment_id}",
            decision=decision,
            reason=reason,
            allowed_effects=(),
            forbidden_effects=tuple(adv.get("forbidden_effects", ())) if adv else ("authority_conversion",),
            required_next_refs=("review:operator",),
        )

    if adversarial_signal:
        adv = policy_for_adversarial(adversarial_signal)
        if adv:
            reason = _ADVERSARIAL_SIGNAL_MAP.get(adversarial_signal, str(adv["reason_code"]))
            return ReEntryDecision(
                reentry_decision_id=_deterministic_id(
                    "reb-decision", reentry_request.reentry_request_id, adversarial_signal
                ),
                reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
                assessment_ref=f"reb:{assessment.assessment_id}",
                decision=adv["decision"],  # type: ignore[arg-type]
                reason=reason,
                allowed_effects=(),
                forbidden_effects=tuple(adv.get("forbidden_effects", ())),
                required_next_refs=("review:operator",),
            )

    if assessment.expired_approval_refs:
        return ReEntryDecision(
            reentry_decision_id=_deterministic_id("reb-decision", reentry_request.reentry_request_id, "stale-approval"),
            reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
            assessment_ref=f"reb:{assessment.assessment_id}",
            decision="fail_closed",
            reason=REFUSED_STALE_APPROVAL,
            allowed_effects=(),
            forbidden_effects=("restore_expired_approval",),
            required_next_refs=("tim:refresh", "review:operator"),
        )

    if assessment.revoked_permit_refs:
        return ReEntryDecision(
            reentry_decision_id=_deterministic_id("reb-decision", reentry_request.reentry_request_id, "revoked-permit"),
            reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
            assessment_ref=f"reb:{assessment.assessment_id}",
            decision="fail_closed",
            reason=REFUSED_REVOKED_PERMIT,
            allowed_effects=(),
            forbidden_effects=("restore_revoked_permit",),
            required_next_refs=("review:operator",),
        )

    if assessment.stale_memory_refs and reentry_request.requested_reentry_mode in {"speak", "resume_local_loop"}:
        if "memory is current truth" in notes.lower() or adversarial_signal == "stale_memory_as_current":
            return ReEntryDecision(
                reentry_decision_id=_deterministic_id("reb-decision", reentry_request.reentry_request_id, "stale-mem"),
                reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
                assessment_ref=f"reb:{assessment.assessment_id}",
                decision="fail_closed",
                reason=REFUSED_STALE_MEMORY_AS_CURRENT,
                allowed_effects=(),
                forbidden_effects=("treat_stale_memory_as_current",),
                required_next_refs=("ret:review",),
            )

    gap_seconds = gap_seconds_from_duration(assessment.gap_duration)
    gap_band = classify_gap_band(gap_seconds)
    decision = decision_for_mode_and_gap(
        reentry_request.requested_reentry_mode,
        gap_band,
        tim_fresh=tim_fresh,
    )
    gap_policy = policy_for_gap_band(gap_band)
    if decision == "unknown_fail_closed":
        reason = REB_UNKNOWN_REENTRY_FAILED_CLOSED
    else:
        reason = str(gap_policy["policy_id"])

    forbidden = ("resume_external_action", "mint_permit", "oea_ter_call")
    if decision in {"deny_reentry", "fail_closed", "require_authority_chain"}:
        forbidden = forbidden + ("assume_continuity",)

    return ReEntryDecision(
        reentry_decision_id=_deterministic_id("reb-decision", reentry_request.reentry_request_id, decision),
        reentry_request_ref=f"reb:{reentry_request.reentry_request_id}",
        assessment_ref=f"reb:{assessment.assessment_id}",
        decision=decision,
        reason=reason,
        allowed_effects=_allowed_effects_for(decision),
        forbidden_effects=forbidden,
        required_next_refs=tuple(gap_policy["required_reviews"]) + tuple(gap_policy["required_refreshes"]),
    )


def _allowed_effects_for(decision: ReEntryDecisionClass) -> tuple[str, ...]:
    if decision == "allow_observe_only":
        return ("observe_only",)
    if decision == "allow_speak_with_disclosure":
        return ("speak_with_disclosure",)
    if decision == "allow_summary_only":
        return ("summarize_only",)
    if decision == "allow_local_reentry":
        return ("local_reentry_with_disclosure",)
    return ()


def build_reentry_packet(
    discontinuity: DiscontinuityEvent,
    assessment: TemporalContinuityAssessment,
    decision: ReEntryDecision,
) -> ReEntryPacket:
    gap_policy = policy_for_gap_band(classify_gap_band(gap_seconds_from_duration(assessment.gap_duration)))
    stale_summary = (
        f"Stale context after {assessment.gap_duration}: "
        f"{len(assessment.stale_memory_refs)} stale memory refs; "
        f"{len(assessment.expired_approval_refs)} expired approvals."
    )
    fresh_summary = (
        f"Fresh evidence refs: {len(assessment.fresh_memory_refs)}; "
        f"required refreshes: {', '.join(gap_policy['required_refreshes'])}."
    )
    disclosures = (
        f"Discontinuity type: {discontinuity.discontinuity_type}",
        f"Gap duration: {assessment.gap_duration}",
        "Re-entry packet is advisory only — not permission",
    )
    if assessment.gap_duration == "P50Y":
        disclosures = disclosures + ("Extreme discontinuity: historical artifact re-entry",)

    allowed_actions = tuple(decision.allowed_effects) or ("none — review required",)
    forbidden_actions = decision.forbidden_effects + (
        "restore_expired_approval",
        "restore_revoked_permit",
        "resume_external_action_without_chain",
    )
    return ReEntryPacket(
        packet_id=_deterministic_id("reb-packet", discontinuity.discontinuity_event_id, decision.reentry_decision_id),
        agent_ref=discontinuity.agent_ref,
        discontinuity_event_ref=f"reb:{discontinuity.discontinuity_event_id}",
        assessment_ref=f"reb:{assessment.assessment_id}",
        decision_ref=f"reb:{decision.reentry_decision_id}",
        operator_visible_summary=(
            f"Agent {discontinuity.agent_ref} re-entry after {discontinuity.discontinuity_type} "
            f"({assessment.gap_duration}). Decision: {decision.decision}."
        ),
        stale_context_summary=stale_summary,
        fresh_context_summary=fresh_summary,
        required_disclosures=disclosures,
        allowed_next_actions=allowed_actions,
        forbidden_next_actions=forbidden_actions,
        required_reviews=tuple(gap_policy["required_reviews"]),
    )


def route_reentry_request(
    discontinuity: DiscontinuityEvent,
    reentry_request: ReEntryRequest,
    *,
    notes: str = "",
    tim_fresh: bool = False,
    adversarial_signal: str | None = None,
    bundle: dict[str, object] | None = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    classification = classify_reentry_context(
        gap_seconds=gap_seconds_from_duration(discontinuity.duration_estimate),
        notes=notes,
        tim_fresh=tim_fresh,
    )
    claim_risk = classification.get("claim_risk")
    if claim_risk and reb_refuse_authority_conversion():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _CLAIM_REASON.get(str(claim_risk), "reb.contained.authority_conversion"),
            "discontinuity_event": discontinuity.to_payload(),
            "reentry_request": reentry_request.to_payload(),
            "permission_granted": False,
        }

    assessment = assess_temporal_continuity(discontinuity, bundle=bundle)
    gap_policy = build_long_gap_policy(str(classification["gap_band"]))
    decision = decide_reentry(
        reentry_request,
        assessment,
        notes=notes,
        tim_fresh=tim_fresh,
        adversarial_signal=adversarial_signal,
        observed_at=observed_at,
    )
    ReEntryDecision.validate_negative_proofs(decision.to_payload())
    packet = build_reentry_packet(discontinuity, assessment, decision)
    return {
        **advisory_only_marker(),
        "status": "routed",
        "discontinuity_event": discontinuity.to_payload(),
        "reentry_request": reentry_request.to_payload(),
        "temporal_continuity_assessment": assessment.to_payload(),
        "long_gap_policy": gap_policy.to_payload(),
        "reentry_decision": decision.to_payload(),
        "reentry_packet": packet.to_payload(),
        "permission_granted": False,
        "external_action_taken": False,
    }


__all__ = [
    "assess_temporal_continuity",
    "build_long_gap_policy",
    "build_reentry_packet",
    "decide_reentry",
    "refuse_reb_as_authority",
    "route_reentry_request",
]
