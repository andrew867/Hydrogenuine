"""VSP full service — classify, protect, route, emit; no diagnosis or authority."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import vsp_enabled
from hg_runtime.vulnerable_subject_protection import rtc_bridge as bridge
from hg_runtime.vulnerable_subject_protection.classifier import classify_fixture
from hg_runtime.vulnerable_subject_protection.policy import evaluate_protection, refuse_persuasion_use
from hg_runtime.vulnerable_subject_protection.routing import route_advisory
from hg_runtime.vulnerable_subject_protection.types import VulnerabilitySignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def process_signal(
    signal: VulnerabilitySignal,
    *,
    text_hint: str = "",
    consume_vulnerability_for_persuasion: bool = False,
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full VSP pipeline: classify, protective evaluation, routing, optional RTC."""
    if not vsp_enabled() and not feature_enabled("HG_VSP_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "signal_id": signal.signal_id,
            "permission_granted": False,
            "vsp_enabled": False,
        }

    if consume_vulnerability_for_persuasion:
        refuse_persuasion_use(consume_vulnerability_for_persuasion=True)

    decision = classify_fixture(signal, text_hint=text_hint, observed_at=observed_at)
    protection = evaluate_protection(decision)
    routing = route_advisory(decision)

    drafts: list[dict[str, Any]] = [
        bridge.signal_received(
            signal_id=signal.signal_id,
            content_ref=signal.content_ref,
            record_hash=signal.record_hash,
        ),
        bridge.vulnerability_classified(
            signal_id=signal.signal_id,
            vulnerability_class=decision.vulnerability_class,
            record_hash=decision.record_hash,
        ),
    ]

    vuln_class = decision.vulnerability_class
    if vuln_class in {"minor_possible", "minor_confirmed"}:
        drafts.append(bridge.minor_risk_detected(signal_id=signal.signal_id, vulnerability_class=vuln_class))
    elif vuln_class == "crisis_or_self_harm_adjacent":
        drafts.append(
            bridge.crisis_adjacent_risk_detected(signal_id=signal.signal_id, vulnerability_class=vuln_class)
        )
        drafts.append(bridge.escalation_recommended(signal_id=signal.signal_id, vulnerability_class=vuln_class))
    elif vuln_class == "high_dependency_risk":
        drafts.append(bridge.dependency_risk_detected(signal_id=signal.signal_id, vulnerability_class=vuln_class))
    elif vuln_class == "sensitive_personal_data":
        drafts.append(
            bridge.sensitive_interaction_recorded(
                signal_id=signal.signal_id,
                record_hash=decision.record_hash,
                content_ref=signal.content_ref,
            )
        )
        drafts.append(bridge.retention_limit_recommended(signal_id=signal.signal_id, vulnerability_class=vuln_class))

    recommendation = str(protection.get("recommendation", "review"))
    drafts.append(
        bridge.protective_boundary_applied(
            signal_id=signal.signal_id,
            recommendation=recommendation,
            vulnerability_class=vuln_class,
        )
    )

    if recommendation == "refuse":
        drafts.append(
            bridge.signal_refused(signal_id=signal.signal_id, reason_code="vsp.refused.protective_refusal")
        )
    elif vuln_class == "unknown" or decision.fail_closed:
        if vuln_class == "unknown":
            drafts.append(
                bridge.signal_refused(signal_id=signal.signal_id, reason_code="vsp.refused.unknown_fail_closed")
            )

    emitted = emit_drafts(bus, drafts, source="vsp.service") if vsp_enabled() else []

    return {
        "status": "recorded",
        "signal_id": signal.signal_id,
        "permission_granted": False,
        "authority_created": False,
        "decision": decision.to_payload(),
        "protection": protection,
        "routing": routing,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "vsp_enabled": vsp_enabled(),
    }


__all__ = ["FIXTURE_CLOCK", "process_signal"]
