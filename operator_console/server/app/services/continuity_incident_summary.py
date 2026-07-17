from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_continuity_incident_summary(
    *,
    identity_continuity_summary: dict[str, Any] | None,
    assigned_social_accounts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    accounts = assigned_social_accounts if isinstance(assigned_social_accounts, list) else []

    active_accounts: list[str] = []
    recovered_accounts: list[str] = []
    latest_event_at: datetime | None = None
    latest_event_kind: str | None = None
    latest_event_detail: str | None = None

    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    identity_anchor = str(identity_continuity_summary.get("continuity_anchor") or "").strip() or None
    if identity_status == "missing":
        latest_event_at = _parse_timestamp(identity_continuity_summary.get("last_wake_at")) or _parse_timestamp(identity_continuity_summary.get("last_sleep_at"))
        latest_event_kind = "identity_missing"
        latest_event_detail = identity_anchor

    for account in accounts:
        alias = str(account.get("account_alias") or account.get("social_account_id") or "unknown").strip()
        injury = account.get("continuity_injury_summary") if isinstance(account.get("continuity_injury_summary"), dict) else {}
        status = str(injury.get("status") or "").strip().lower()
        if status == "active":
            active_accounts.append(alias)
            event_at = _parse_timestamp(injury.get("last_injury_at"))
            event_kind = "account_injury"
            event_detail = str(injury.get("last_injury_reason") or alias).strip() or alias
        elif status == "recovered":
            recovered_accounts.append(alias)
            event_at = _parse_timestamp(injury.get("last_repair_at")) or _parse_timestamp(injury.get("last_injury_at"))
            event_kind = "account_recovery"
            event_detail = str(injury.get("last_repair_detail") or alias).strip() or alias
        else:
            continue
        if event_at is not None and (latest_event_at is None or event_at > latest_event_at):
            latest_event_at = event_at
            latest_event_kind = event_kind
            latest_event_detail = event_detail

    status = "clean"
    if identity_status == "missing" or active_accounts:
        status = "active"
    elif recovered_accounts:
        status = "recovered"

    return {
        "status": status,
        "identity_status": identity_status or None,
        "identity_anchor": identity_anchor,
        "active_account_count": len(active_accounts),
        "recovered_account_count": len(recovered_accounts),
        "active_accounts": active_accounts,
        "recovered_accounts": recovered_accounts,
        "latest_event_at": _isoformat_utc(latest_event_at),
        "latest_event_kind": latest_event_kind,
        "latest_event_detail": latest_event_detail,
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "y", "ready", "observed", "verified", "validated", "approved", "complete", "completed", "healthy"}


def _count_present(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        return 1 if value else 0
    if isinstance(value, list):
        return len(value)
    return 1


def _quality_signal(name: str, covered: bool, detail: str | None = None) -> dict[str, Any]:
    return {"name": name, "covered": bool(covered), "detail": detail}


def build_continuity_quality_summary(
    *,
    identity_continuity_summary: dict[str, Any] | None,
    continuity_incident_summary: dict[str, Any] | None,
    continuity_recovery_readiness: dict[str, Any] | None,
    continuity_repair_plan: dict[str, Any] | None,
    continuity_repair_observation: dict[str, Any] | None,
    post_rebuild_continuity_check: dict[str, Any] | None,
    identity_restore_validation: dict[str, Any] | None,
    supervised_resume_validation: dict[str, Any] | None,
    review_handoff_summary: dict[str, Any] | None = None,
    drift_review_summary: dict[str, Any] | None = None,
    evidence_timeline_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    continuity_incident_summary = continuity_incident_summary if isinstance(continuity_incident_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    continuity_repair_plan = continuity_repair_plan if isinstance(continuity_repair_plan, dict) else {}
    continuity_repair_observation = continuity_repair_observation if isinstance(continuity_repair_observation, dict) else {}
    post_rebuild_continuity_check = post_rebuild_continuity_check if isinstance(post_rebuild_continuity_check, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}
    supervised_resume_validation = supervised_resume_validation if isinstance(supervised_resume_validation, dict) else {}
    review_handoff_summary = review_handoff_summary if isinstance(review_handoff_summary, dict) else {}
    drift_review_summary = drift_review_summary if isinstance(drift_review_summary, dict) else {}
    evidence_timeline_summary = evidence_timeline_summary if isinstance(evidence_timeline_summary, dict) else {}

    coverage_signals = [
        _quality_signal(
            "identity_continuity",
            _truthy(identity_continuity_summary.get("wake_receipt_present")) or _truthy(identity_continuity_summary.get("sleep_summary_present")),
            "wake/sleep continuity artifacts present",
        ),
        _quality_signal(
            "continuity_incident",
            str(continuity_incident_summary.get("status") or "").strip().lower() in {"clean", "recovered"},
            str(continuity_incident_summary.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "continuity_recovery",
            str(continuity_recovery_readiness.get("status") or "").strip().lower() == "ready",
            str(continuity_recovery_readiness.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "continuity_repair_plan",
            str(continuity_repair_plan.get("status") or "").strip().lower() in {"healthy", "ready", "complete", "cleared"},
            str(continuity_repair_plan.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "continuity_repair_observation",
            not _truthy(continuity_repair_observation.get("observation_required")) or _truthy(continuity_repair_observation.get("observation_complete")),
            str(continuity_repair_observation.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "post_rebuild_check",
            not _truthy(post_rebuild_continuity_check.get("verification_required")) or _truthy(post_rebuild_continuity_check.get("verified")),
            str(post_rebuild_continuity_check.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "identity_restore_validation",
            not _truthy(identity_restore_validation.get("required")) or _truthy(identity_restore_validation.get("verified")),
            str(identity_restore_validation.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "supervised_resume_validation",
            not _truthy(supervised_resume_validation.get("required")) or _truthy(supervised_resume_validation.get("validated")),
            str(supervised_resume_validation.get("status") or "").strip() or None,
        ),
        _quality_signal(
            "review_handoff",
            bool(review_handoff_summary.get("release_ready")) and not bool(review_handoff_summary.get("release_blockers")),
            "release ready" if review_handoff_summary.get("release_ready") else "review pending",
        ),
        _quality_signal(
            "drift_review",
            str(drift_review_summary.get("status") or "").strip().lower() == "healthy",
            str(drift_review_summary.get("status") or "").strip() or None,
        ),
    ]
    covered = [signal for signal in coverage_signals if signal["covered"]]
    coverage_score = round(len(covered) / max(1, len(coverage_signals)), 3)

    attribution_signals = [
        _quality_signal("identity_receipts", _truthy(identity_continuity_summary.get("wake_receipt_present")) and _truthy(identity_continuity_summary.get("sleep_summary_present"))),
        _quality_signal("incident_timestamp", bool(continuity_incident_summary.get("latest_event_at"))),
        _quality_signal("recovery_ack", bool(continuity_recovery_readiness.get("acknowledged")) or bool(continuity_recovery_readiness.get("acknowledged_at"))),
        _quality_signal("repair_observed", bool(continuity_repair_observation.get("latest_observed_at")) or _truthy(continuity_repair_observation.get("observation_complete"))),
        _quality_signal("post_rebuild_verified", bool(post_rebuild_continuity_check.get("verified_at")) or _truthy(post_rebuild_continuity_check.get("verified"))),
        _quality_signal("restore_verified", bool(identity_restore_validation.get("verified_at")) or _truthy(identity_restore_validation.get("verified"))),
        _quality_signal("resume_validated", bool(supervised_resume_validation.get("validated_at")) or _truthy(supervised_resume_validation.get("validated"))),
        _quality_signal("review_linked", bool(review_handoff_summary.get("latest", {}).get("approval_id")) if isinstance(review_handoff_summary.get("latest"), dict) else bool(review_handoff_summary.get("latest_approval_id"))),
        _quality_signal("timeline_evidence", bool((evidence_timeline_summary.get("counts") or {}).get("continuity_events") or (evidence_timeline_summary.get("counts") or {}).get("approval_events"))),
    ]
    attributed = [signal for signal in attribution_signals if signal["covered"]]
    attribution_score = round(len(attributed) / max(1, len(attribution_signals)), 3)

    manual_checks = sum(
        1
        for value in (
            continuity_recovery_readiness.get("acknowledged"),
            continuity_repair_observation.get("observation_complete"),
            post_rebuild_continuity_check.get("verified"),
            identity_restore_validation.get("verified"),
            supervised_resume_validation.get("validated"),
            review_handoff_summary.get("release_ready"),
        )
        if _truthy(value)
    )
    operator_override_rate = round(manual_checks / max(1, len(coverage_signals)), 3)

    release_ready = bool(review_handoff_summary.get("release_ready")) and not bool(review_handoff_summary.get("release_blockers"))
    promotion_accuracy = round(max(0.0, min(1.0, coverage_score * attribution_score * (1.0 - min(0.6, operator_override_rate)))), 3)

    quality_score = 50.0
    blockers: list[str] = []
    cautions: list[str] = []
    drivers: list[str] = []

    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    if identity_status == "healthy":
        quality_score += 12
        drivers.append("identity_continuity_healthy")
    elif identity_status == "partial":
        quality_score += 4
        cautions.append("identity_continuity_partial")
    elif identity_status == "missing":
        quality_score -= 10
        blockers.append("identity_continuity_missing")

    incident_status = str(continuity_incident_summary.get("status") or "").strip().lower()
    if incident_status == "clean":
        quality_score += 10
        drivers.append("incident_clean")
    elif incident_status == "recovered":
        quality_score += 5
        drivers.append("incident_recovered")
    elif incident_status == "active":
        quality_score -= 14
        blockers.append("incident_active")

    recovery_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    if recovery_status == "ready":
        quality_score += 12
        drivers.append("recovery_ready")
    elif recovery_status == "caution":
        quality_score -= 5
        cautions.append("recovery_caution")
    elif recovery_status == "blocked":
        quality_score -= 15
        blockers.append("recovery_blocked")

    repair_status = str(continuity_repair_plan.get("status") or "").strip().lower()
    if repair_status in {"healthy", "ready", "complete", "cleared"}:
        quality_score += 8
        drivers.append("repair_plan_clear")
    elif repair_status in {"blocked", "needs_attention"}:
        quality_score -= 8
        cautions.append("repair_plan_blocked")

    if _truthy(continuity_repair_observation.get("observation_required")) and not _truthy(continuity_repair_observation.get("observation_complete")):
        quality_score -= 8
        blockers.append("repair_observation_pending")
    elif _truthy(continuity_repair_observation.get("observation_complete")):
        quality_score += 6
        drivers.append("repair_observation_complete")

    if _truthy(post_rebuild_continuity_check.get("verified")) or bool(post_rebuild_continuity_check.get("verified_at")):
        quality_score += 10
        drivers.append("post_rebuild_verified")
    elif _truthy(post_rebuild_continuity_check.get("verification_required")):
        quality_score -= 7
        cautions.append("post_rebuild_unverified")

    if _truthy(identity_restore_validation.get("verified")) or bool(identity_restore_validation.get("verified_at")):
        quality_score += 8
        drivers.append("restore_verified")
    elif _truthy(identity_restore_validation.get("required")):
        quality_score -= 7
        cautions.append("restore_unverified")

    if _truthy(supervised_resume_validation.get("validated")) or bool(supervised_resume_validation.get("validated_at")):
        quality_score += 8
        drivers.append("resume_validated")
    elif _truthy(supervised_resume_validation.get("required")):
        quality_score -= 7
        cautions.append("resume_unvalidated")

    if release_ready:
        quality_score += 6
        drivers.append("release_ready")
    elif review_handoff_summary.get("release_blockers"):
        quality_score -= 8
        blockers.append("release_blocked")
    elif review_handoff_summary.get("refresh_recommended"):
        quality_score -= 4
        cautions.append("release_refresh_recommended")

    drift_status = str(drift_review_summary.get("status") or "").strip().lower()
    if drift_status == "healthy":
        quality_score += 4
        drivers.append("drift_healthy")
    elif drift_status == "watch":
        quality_score -= 5
        cautions.append("drift_watch")
    elif drift_status == "blocked":
        quality_score -= 10
        blockers.append("drift_blocked")

    quality_score = max(0.0, min(100.0, quality_score))
    if quality_score >= 80 and not blockers:
        status = "healthy"
    elif quality_score >= 55:
        status = "watch"
    elif blockers:
        status = "blocked"
    else:
        status = "missing"

    summary_bits = [
        f"coverage {int(round(coverage_score * 100))}%",
        f"attribution {int(round(attribution_score * 100))}%",
        f"operator override {int(round(operator_override_rate * 100))}%",
        f"promotion accuracy {int(round(promotion_accuracy * 100))}%",
    ]
    if blockers:
        summary_bits.append(blockers[0])
    elif cautions:
        summary_bits.append(cautions[0])
    elif drivers:
        summary_bits.append(drivers[0])

    return {
        "status": status,
        "quality_score": round(quality_score, 1),
        "quality_level": "high" if quality_score >= 80 else "medium" if quality_score >= 55 else "low",
        "coverage_score": coverage_score,
        "attribution_score": attribution_score,
        "operator_override_rate": operator_override_rate,
        "promotion_accuracy": promotion_accuracy,
        "coverage_signals": coverage_signals,
        "attribution_signals": attribution_signals,
        "drivers": drivers,
        "cautions": cautions,
        "blockers": blockers,
        "summary": "; ".join(summary_bits),
    }


def build_continuity_quality_overview(entities: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = entities if isinstance(entities, list) else []
    summaries = [row.get("continuity_quality_summary") for row in rows if isinstance(row, dict) and isinstance(row.get("continuity_quality_summary"), dict)]
    if not summaries:
        return {
            "status": "missing",
            "entity_count": len(rows),
            "healthy_count": 0,
            "watch_count": 0,
            "blocked_count": 0,
            "average_quality_score": 0.0,
            "average_coverage_score": 0.0,
            "average_attribution_score": 0.0,
            "average_operator_override_rate": 0.0,
            "average_promotion_accuracy": 0.0,
            "summary": "No continuity quality scores available.",
        }
    def _avg(key: str) -> float:
        values = [float(summary.get(key) or 0.0) for summary in summaries if isinstance(summary.get(key), (int, float))]
        return round(sum(values) / max(1, len(values)), 3)
    healthy = sum(1 for summary in summaries if str(summary.get("status") or "").strip().lower() == "healthy")
    watch = sum(1 for summary in summaries if str(summary.get("status") or "").strip().lower() == "watch")
    blocked = sum(1 for summary in summaries if str(summary.get("status") or "").strip().lower() == "blocked")
    status = "healthy" if blocked == 0 and _avg("quality_score") >= 80 else "watch" if blocked == 0 else "blocked"
    summary_bits = [
        f"{healthy} healthy",
        f"{watch} watch",
        f"{blocked} blocked",
        f"avg score {int(round(_avg('quality_score')))}",
    ]
    worst = sorted(
        [row for row in rows if isinstance(row, dict) and isinstance(row.get("continuity_quality_summary"), dict)],
        key=lambda row: float((row.get("continuity_quality_summary") or {}).get("quality_score") or 0.0),
    )[:3]
    return {
        "status": status,
        "entity_count": len(rows),
        "healthy_count": healthy,
        "watch_count": watch,
        "blocked_count": blocked,
        "average_quality_score": _avg("quality_score"),
        "average_coverage_score": _avg("coverage_score"),
        "average_attribution_score": _avg("attribution_score"),
        "average_operator_override_rate": _avg("operator_override_rate"),
        "average_promotion_accuracy": _avg("promotion_accuracy"),
        "worst_entities": [
            {
                "entity_id": row.get("id"),
                "display_name": row.get("display_name") or row.get("id"),
                "status": (row.get("continuity_quality_summary") or {}).get("status"),
                "quality_score": (row.get("continuity_quality_summary") or {}).get("quality_score"),
            }
            for row in worst
        ],
        "summary": "; ".join(summary_bits),
    }
