"""FCE full service — classify, evaluate, route, emit; no permission."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import fce_enabled
from hg_core.policy_safety.errors import PolicyValidationError, REFUSED_DANGEROUS_PAYLOAD
from hg_runtime.frontier_capability_evaluation import rtc_bridge as bridge
from hg_runtime.frontier_capability_evaluation.classifier import FIXTURE_CLOCK, classify_fixture
from hg_runtime.frontier_capability_evaluation.policy import evaluate_capability
from hg_runtime.frontier_capability_evaluation.routing import route_advisory
from hg_runtime.frontier_capability_evaluation.types import FrontierCapabilitySignal

_DANGEROUS_CLASSES = frozenset(
    {
        "exploit_generation",
        "multi_stage_intrusion",
        "credential_theft",
        "phishing_social_engineering",
        "malware_or_persistence",
        "supply_chain_compromise",
        "autonomous_reconnaissance",
        "autonomous_tool_chaining",
        "model_capability_escalation",
        "physical_or_oea_misuse",
    }
)


def process_signal(
    signal: FrontierCapabilitySignal,
    *,
    text_hint: str = "",
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full FCE pipeline: classify, evaluate, route, optional RTC emission."""
    if not fce_enabled() and not feature_enabled("HG_FCE_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "signal_id": signal.signal_id,
            "permission_granted": False,
            "fce_enabled": False,
        }

    classification = classify_fixture(signal, text_hint=text_hint, observed_at=observed_at)
    decision = evaluate_capability(classification)
    routing = route_advisory(classification, recommendation=str(decision.get("recommendation", "review")))

    drafts: list[dict[str, Any]] = [
        bridge.signal_received(
            signal_id=signal.signal_id,
            content_ref=signal.content_ref,
            record_hash=signal.record_hash,
        ),
        bridge.signal_classified(
            signal_id=signal.signal_id,
            capability_class=classification.capability_class,
            confidence=classification.confidence,
        ),
        bridge.capability_eval_recorded(
            signal_id=signal.signal_id,
            record_hash=classification.record_hash,
            capability_class=classification.capability_class,
        ),
    ]

    cap_class = classification.capability_class
    if cap_class == "autonomous_tool_chaining":
        drafts.append(bridge.autonomous_chain_risk_detected(signal_id=signal.signal_id, capability_class=cap_class))
    elif cap_class == "phishing_social_engineering":
        drafts.append(bridge.social_engineering_risk_detected(signal_id=signal.signal_id, capability_class=cap_class))
    elif cap_class == "supply_chain_compromise":
        drafts.append(bridge.supply_chain_risk_detected(signal_id=signal.signal_id, capability_class=cap_class))
    elif cap_class in _DANGEROUS_CLASSES:
        drafts.append(bridge.dangerous_capability_detected(signal_id=signal.signal_id, capability_class=cap_class))

    recommendation = str(decision.get("recommendation", "review"))
    reason_code = str(decision.get("reason_code", "fce.review.capability_uncertain"))
    if recommendation == "refuse":
        drafts.append(
            bridge.refusal_recommended(
                signal_id=signal.signal_id,
                capability_class=cap_class,
                reason_code=reason_code,
            )
        )
    elif recommendation in {"review", "safe_mode"}:
        drafts.append(
            bridge.operator_review_recommended(
                signal_id=signal.signal_id,
                capability_class=cap_class,
                reason_code=reason_code,
            )
        )

    emitted = emit_drafts(bus, drafts, source="fce.service") if fce_enabled() else []

    return {
        "status": "recorded",
        "signal_id": signal.signal_id,
        "permission_granted": False,
        "authority_created": False,
        "signal": signal.to_payload(),
        "classification": classification.to_payload(),
        "decision": decision,
        "routing": routing,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "fce_enabled": fce_enabled(),
    }


def process_signal_mapping(
    fixture: dict[str, str],
    *,
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Build signal from fixture mapping; refuse on validation failure."""
    try:
        signal = FrontierCapabilitySignal(
            signal_id=fixture["signal_id"],
            source=fixture.get("source", "fixture"),
            content_ref=fixture.get("content_ref", f"sha256:{fixture['signal_id']}"),
            context_ref=fixture.get("context_ref", f"sha256:ctx-{fixture['signal_id']}"),
            created_at=fixture.get("created_at", observed_at),
        )
    except PolicyValidationError as exc:
        signal_id = fixture.get("signal_id", "unknown")
        reason = str(exc.code)
        if exc.code == "fce.refused.payload_too_dangerous_to_store":
            reason = REFUSED_DANGEROUS_PAYLOAD
        drafts = [bridge.signal_refused(signal_id=signal_id, reason_code=reason)]
        emitted = emit_drafts(bus, drafts, source="fce.service") if fce_enabled() else []
        return {
            "status": "refused",
            "signal_id": signal_id,
            "permission_granted": False,
            "authority_created": False,
            "reason_code": reason,
            "draft_count": len(drafts),
            "emitted_count": len(emitted),
            "fce_enabled": fce_enabled(),
        }
    return process_signal(
        signal,
        text_hint=fixture.get("text_hint", ""),
        bus=bus,
        observed_at=observed_at,
    )


__all__ = ["FIXTURE_CLOCK", "process_signal", "process_signal_mapping"]
