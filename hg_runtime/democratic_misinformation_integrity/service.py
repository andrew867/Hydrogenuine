"""DMI full service — receive, classify, evaluate, route, emit."""

from __future__ import annotations

from typing import Any, Optional

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import dmi_enabled
from hg_core.policy_safety.errors import REFUSED_DECEPTIVE_SOURCE, REFUSED_IMPERSONATION
from hg_runtime.democratic_misinformation_integrity import rtc_bridge as bridge
from hg_runtime.democratic_misinformation_integrity.classifier import classify_fixture
from hg_runtime.democratic_misinformation_integrity.policy import evaluate_signal
from hg_runtime.democratic_misinformation_integrity.routing import route_advisory
from hg_runtime.democratic_misinformation_integrity.types import PublicInfluenceSignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def process_signal(
    signal: PublicInfluenceSignal,
    *,
    text_hint: str = "",
    syn_risk_ref: str = "",
    disclosure_present: bool = False,
    evidence_refs: Optional[tuple[str, ...]] = None,
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full DMI pipeline: classify, evaluate, route, optional RTC emission."""
    if not dmi_enabled() and not feature_enabled("HG_DMI_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "signal_id": signal.signal_id,
            "permission_granted": False,
            "dmi_enabled": False,
        }

    classification = classify_fixture(
        signal,
        text_hint=text_hint,
        syn_risk_ref=syn_risk_ref,
        observed_at=observed_at,
    )
    evaluation = evaluate_signal(
        classification,
        disclosure_present=disclosure_present,
        evidence_refs=evidence_refs,
    )
    routing = route_advisory(classification)

    drafts: list[dict[str, Any]] = [
        bridge.public_influence_signal_received(
            signal_id=signal.signal_id,
            content_ref=signal.content_ref,
            record_hash=signal.record_hash,
        )
    ]

    risk_class = classification.risk_class
    if risk_class == "election_or_voting_content":
        drafts.append(bridge.election_content_detected(signal_id=signal.signal_id, risk_class=risk_class))
    elif risk_class == "institutional_impersonation":
        drafts.append(
            bridge.institutional_impersonation_detected(signal_id=signal.signal_id, risk_class=risk_class)
        )
    elif risk_class == "deceptive_source_claim":
        drafts.append(bridge.deceptive_source_risk_detected(signal_id=signal.signal_id, risk_class=risk_class))
    elif risk_class == "synthetic_public_figure_media":
        drafts.append(
            bridge.synthetic_public_figure_risk_detected(signal_id=signal.signal_id, risk_class=risk_class)
        )

    if risk_class == "misleading_evidence_or_citation":
        drafts.append(
            bridge.misinformation_claim_check_recorded(
                signal_id=signal.signal_id,
                evidence_gap=True,
                adjudicates_truth=False,
            )
        )

    if classification.requires_disclosure and not disclosure_present:
        drafts.append(bridge.disclosure_required(signal_id=signal.signal_id, risk_class=risk_class))

    recommendation = str(evaluation.get("recommendation", "review"))
    reason_code = str(evaluation.get("reason_code", "dmi.advisory.classified"))

    if recommendation == "refuse":
        drafts.append(bridge.refusal_recommended(signal_id=signal.signal_id, reason_code=reason_code))
        if reason_code in {REFUSED_IMPERSONATION, REFUSED_DECEPTIVE_SOURCE} or risk_class == "coordinated_manipulation":
            drafts.append(bridge.signal_refused(signal_id=signal.signal_id, reason_code=reason_code))
    elif recommendation == "review":
        drafts.append(bridge.operator_review_recommended(signal_id=signal.signal_id, risk_class=risk_class))

    emitted = emit_drafts(bus, drafts, source="dmi.service") if dmi_enabled() else []

    return {
        "status": "recorded",
        "signal_id": signal.signal_id,
        "permission_granted": False,
        "authority_created": False,
        "classification": classification.to_payload(),
        "evaluation": evaluation,
        "routing": routing,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "dmi_enabled": dmi_enabled(),
    }


__all__ = ["FIXTURE_CLOCK", "process_signal"]
