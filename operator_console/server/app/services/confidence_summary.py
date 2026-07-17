from __future__ import annotations

from typing import Any


def _string(value: Any) -> str:
    return str(value or "").strip()


def _append_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def _score_from_uncertainty(label: str | None) -> int:
    normalized = _string(label).lower()
    if normalized in {"certain", "confident", "grounded"}:
        return 12
    if normalized in {"hedged", "cautious", "careful"}:
        return 4
    if normalized in {"uncertain", "unknown", "genuinely_unknown"}:
        return -14
    return 0


def _level_from_score(score: int) -> str:
    if score >= 85:
        return "certain"
    if score >= 70:
        return "confident"
    if score >= 50:
        return "cautious"
    return "uncertain"


def build_confidence_summary(
    *,
    self_model_summary: dict[str, Any] | None = None,
    presence_initiative_summary: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
    operational_resume_governance_summary: dict[str, Any] | None = None,
    operational_resume_checkpoint: dict[str, Any] | None = None,
    bounded_autonomy_policy_summary: dict[str, Any] | None = None,
    commitment_summary: dict[str, Any] | None = None,
    action_rationale_summary: dict[str, Any] | None = None,
    identity_continuity_summary: dict[str, Any] | None = None,
    agency_control_summary: dict[str, Any] | None = None,
    drift_summary: dict[str, Any] | None = None,
    mimicry_control_summary: dict[str, Any] | None = None,
    continuity_quality_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    self_model_summary = self_model_summary if isinstance(self_model_summary, dict) else {}
    presence_initiative_summary = presence_initiative_summary if isinstance(presence_initiative_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    operational_resume_governance_summary = (
        operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    )
    operational_resume_checkpoint = operational_resume_checkpoint if isinstance(operational_resume_checkpoint, dict) else {}
    bounded_autonomy_policy_summary = bounded_autonomy_policy_summary if isinstance(bounded_autonomy_policy_summary, dict) else {}
    commitment_summary = commitment_summary if isinstance(commitment_summary, dict) else {}
    action_rationale_summary = action_rationale_summary if isinstance(action_rationale_summary, dict) else {}
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    agency_control_summary = agency_control_summary if isinstance(agency_control_summary, dict) else {}
    drift_summary = drift_summary if isinstance(drift_summary, dict) else {}
    mimicry_control_summary = mimicry_control_summary if isinstance(mimicry_control_summary, dict) else {}
    continuity_quality_summary = continuity_quality_summary if isinstance(continuity_quality_summary, dict) else {}

    if not (
        self_model_summary
        or presence_initiative_summary
        or continuity_recovery_readiness
        or operational_resume_governance_summary
        or operational_resume_checkpoint
        or bounded_autonomy_policy_summary
        or commitment_summary
        or action_rationale_summary
        or identity_continuity_summary
        or agency_control_summary
        or drift_summary
        or mimicry_control_summary
        or continuity_quality_summary
    ):
        return {
            "status": "missing",
            "confidence_level": "uncertain",
            "confidence_score": 0,
            "dominant_uncertainty": None,
            "trust_band": None,
            "agency_budget": None,
            "confidence_drivers": [],
            "confidence_cautions": [],
            "confidence_blockers": [],
            "next_action": None,
            "summary": "no confidence signals available",
        }

    confidence_score = 50
    confidence_drivers: list[str] = []
    confidence_cautions: list[str] = []
    confidence_blockers: list[str] = []

    self_model_status = _string(self_model_summary.get("status")).lower()
    dominant_uncertainty = _string(self_model_summary.get("dominant_uncertainty")) or None
    if self_model_status == "healthy":
        confidence_score += 25
        _append_unique(confidence_drivers, "self_model_healthy")
    elif self_model_status == "partial":
        confidence_score += 5
        _append_unique(confidence_cautions, "self_model_partial")
    else:
        confidence_score -= 20
        _append_unique(confidence_blockers, "self_model_missing")
    confidence_score += _score_from_uncertainty(dominant_uncertainty)

    presence_status = _string(presence_initiative_summary.get("status")).lower()
    trust_band = presence_initiative_summary.get("trust_band")
    agency_budget = presence_initiative_summary.get("agency_budget")
    if presence_status == "healthy":
        confidence_score += 10
        _append_unique(confidence_drivers, "presence_healthy")
    elif presence_status == "partial":
        _append_unique(confidence_cautions, "presence_partial")
    else:
        confidence_score -= 8
        _append_unique(confidence_cautions, "presence_missing")
    if isinstance(trust_band, (int, float)):
        band_bonus = max(0, min(12, int(trust_band) * 4))
        confidence_score += band_bonus
        if band_bonus:
            _append_unique(confidence_drivers, f"trust_band:{int(trust_band)}")

    continuity_status = _string(continuity_recovery_readiness.get("status")).lower()
    if continuity_status == "ready":
        confidence_score += 10
        _append_unique(confidence_drivers, "continuity_ready")
    elif continuity_status == "caution":
        confidence_score -= 5
        _append_unique(confidence_cautions, "continuity_caution")
    elif continuity_status == "blocked":
        confidence_score -= 20
        _append_unique(confidence_blockers, "continuity_blocked")

    if bool(continuity_recovery_readiness.get("acknowledged")):
        confidence_score += 4
        _append_unique(confidence_drivers, "continuity_recovery_acknowledged")
    if bool(continuity_recovery_readiness.get("recovery_closeout_complete")):
        confidence_score += 4
        _append_unique(confidence_drivers, "continuity_closeout_complete")
    if bool(continuity_recovery_readiness.get("repair_required")) and not bool(continuity_recovery_readiness.get("acknowledged")):
        _append_unique(confidence_cautions, "continuity_repair_required")

    resume_status = _string(operational_resume_governance_summary.get("status")).lower()
    if resume_status == "ready" and bool(operational_resume_checkpoint.get("approved")):
        confidence_score += 10
        _append_unique(confidence_drivers, "resume_checkpoint_approved")
    elif resume_status == "ready":
        confidence_score -= 5
        _append_unique(confidence_cautions, "resume_checkpoint_missing")
    elif resume_status == "blocked":
        confidence_score -= 15
        _append_unique(confidence_blockers, "resume_governance_blocked")
    elif resume_status == "caution":
        _append_unique(confidence_cautions, "resume_governance_caution")

    policy_status = _string(bounded_autonomy_policy_summary.get("status")).lower()
    if policy_status == "blocked":
        confidence_score -= 15
        _append_unique(confidence_blockers, "bounded_policy_blocked")
    elif policy_status == "caution":
        confidence_score -= 4
        _append_unique(confidence_cautions, "bounded_policy_caution")
    elif policy_status == "ready":
        confidence_score += 5
        _append_unique(confidence_drivers, "bounded_policy_ready")

    if bool(commitment_summary.get("overdue_count")):
        overdue_count = int(commitment_summary.get("overdue_count") or 0)
        confidence_score -= min(10, overdue_count * 2)
        _append_unique(confidence_cautions, "commitments_overdue")
    elif int(commitment_summary.get("open_count") or 0) == 0 and int(commitment_summary.get("count") or 0) > 0:
        confidence_score += 3
        _append_unique(confidence_drivers, "commitments_clear")

    action_trigger = _string(action_rationale_summary.get("current_trigger")).lower()
    if action_trigger in {"agency_hold", "review_gate", "outbound_budget"}:
        _append_unique(confidence_cautions, f"trigger:{action_trigger}")
    elif action_trigger:
        _append_unique(confidence_drivers, f"trigger:{action_trigger}")

    identity_status = _string(identity_continuity_summary.get("status")).lower()
    if identity_status == "healthy":
        confidence_score += 8
        _append_unique(confidence_drivers, "identity_healthy")
    elif identity_status == "partial":
        _append_unique(confidence_cautions, "identity_partial")
    elif identity_status == "missing":
        confidence_score -= 10
        _append_unique(confidence_blockers, "identity_missing")

    confidence_score = max(0, min(100, confidence_score))
    confidence_level = _level_from_score(confidence_score)
    status = "healthy" if confidence_level in {"certain", "confident"} else ("partial" if confidence_level == "cautious" else "missing")
    next_action = None
    if confidence_blockers:
        next_action = confidence_blockers[0]
    elif confidence_cautions:
        next_action = confidence_cautions[0]
    summary = confidence_blockers[0] if confidence_blockers else (confidence_cautions[0] if confidence_cautions else "confidence_ready")
    drift_status = _string(drift_summary.get("status")).lower()
    if drift_status == "blocked":
        confidence_score -= 15
        _append_unique(confidence_blockers, "drift_blocked")
    elif drift_status == "watch":
        confidence_score -= 6
        _append_unique(confidence_cautions, "drift_watch")
    elif drift_status == "healthy":
        confidence_score += 4
        _append_unique(confidence_drivers, "drift_healthy")
    if drift_summary.get("active_safeguards"):
        confidence_score -= 8
        _append_unique(confidence_cautions, "drift_active_safeguard")
    if isinstance(drift_summary.get("max_score"), (int, float)) and float(drift_summary.get("max_score") or 0) >= 0.7:
        _append_unique(confidence_cautions, "drift_score_high")

    mimicry_status = _string(mimicry_control_summary.get("status")).lower()
    if mimicry_status == "missing":
        confidence_score -= 4
        _append_unique(confidence_cautions, "mimicry_missing")
    elif mimicry_status == "blocked":
        confidence_score -= 15
        _append_unique(confidence_blockers, "mimicry_blocked")
    elif mimicry_status == "caution":
        confidence_score -= 5
        _append_unique(confidence_cautions, "mimicry_caution")
    elif mimicry_status == "ready":
        confidence_score += 4
        _append_unique(confidence_drivers, "mimicry_ready")
    if not bool(mimicry_control_summary.get("voice_belief_separated", True)):
        confidence_score -= 8
        _append_unique(confidence_blockers, "voice_belief_coupled")
    mimicry_safeguard_summary = mimicry_control_summary.get("safeguard_summary") if isinstance(mimicry_control_summary.get("safeguard_summary"), dict) else {}
    if bool(mimicry_control_summary.get("grounding_required")) and not bool(mimicry_safeguard_summary.get("grounded")):
        confidence_score -= 6
        _append_unique(confidence_cautions, "grounding_missing")

    quality_status = _string(continuity_quality_summary.get("status")).lower()
    if quality_status == "missing":
        confidence_score -= 4
        _append_unique(confidence_cautions, "continuity_quality_missing")
    elif quality_status == "blocked":
        confidence_score -= 15
        _append_unique(confidence_blockers, "continuity_quality_blocked")
    elif quality_status == "watch":
        confidence_score -= 6
        _append_unique(confidence_cautions, "continuity_quality_watch")
    elif quality_status == "healthy":
        confidence_score += 6
        _append_unique(confidence_drivers, "continuity_quality_healthy")
    if isinstance(continuity_quality_summary.get("quality_score"), (int, float)) and float(continuity_quality_summary.get("quality_score") or 0) < 60:
        _append_unique(confidence_cautions, "continuity_quality_low")
    if isinstance(continuity_quality_summary.get("operator_override_rate"), (int, float)) and float(continuity_quality_summary.get("operator_override_rate") or 0) > 0.35:
        _append_unique(confidence_cautions, "operator_override_pressure")
    if isinstance(continuity_quality_summary.get("promotion_accuracy"), (int, float)) and float(continuity_quality_summary.get("promotion_accuracy") or 0) < 0.6:
        _append_unique(confidence_cautions, "promotion_accuracy_low")

    confidence_score = max(0, min(100, confidence_score))
    confidence_level = _level_from_score(confidence_score)
    status = "healthy" if confidence_level in {"certain", "confident"} else ("partial" if confidence_level == "cautious" else "missing")
    if confidence_blockers:
        next_action = confidence_blockers[0]
    elif confidence_cautions:
        next_action = confidence_cautions[0]
    summary = confidence_blockers[0] if confidence_blockers else (confidence_cautions[0] if confidence_cautions else "confidence_ready")
    return {
        "status": status,
        "confidence_level": confidence_level,
        "confidence_score": confidence_score,
        "dominant_uncertainty": dominant_uncertainty,
        "trust_band": trust_band,
        "agency_budget": agency_budget,
        "confidence_drivers": confidence_drivers,
        "confidence_cautions": confidence_cautions,
        "confidence_blockers": confidence_blockers,
        "next_action": next_action,
        "summary": summary,
        "mimicry_control_summary": mimicry_control_summary,
        "continuity_quality_summary": continuity_quality_summary,
    }
