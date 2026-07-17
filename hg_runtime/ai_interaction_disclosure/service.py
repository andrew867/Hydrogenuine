"""AID full service — assemble cards, consume feeds, emit, no permission."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import aid_enabled
from hg_core.policy_safety.errors import REFUSED_UNPROVEN_CAPABILITY
from hg_runtime.ai_interaction_disclosure import rtc_bridge as bridge
from hg_runtime.ai_interaction_disclosure.disclosure import (
    FIXTURE_CLOCK,
    build_disclosure_card,
    detect_missing_disclosure,
)
from hg_runtime.ai_interaction_disclosure.mode_card import build_mode_card
from hg_runtime.ai_interaction_disclosure.policy import CapabilityLimitCard, evaluate_capability_limit, evaluate_disclosure_policy
from hg_runtime.ai_interaction_disclosure.routing import route_advisory
from hg_runtime.ai_interaction_disclosure.uncertainty import assemble_generated_content, assemble_uncertainty

FIXTURE = {
    "disclosure_id": "aid-fixture",
    "runtime_mode": "proposal_only",
    "model_or_provider_label": "fixture-model",
    "capability_claim": "",
    "capability_evidence_ref": "",
    "content_generated_status": "none",
    "uncertainty_summary": "fixture_slice",
    "known_limitations": "offline_fixture",
}


def process_disclosure(
    fixture: Mapping[str, str],
    *,
    syn_feed: Mapping[str, str] | None = None,
    trl_feed: Mapping[str, str] | None = None,
    sab_feed: Mapping[str, str] | None = None,
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full AID pipeline: cards, feed consumption, routing, optional RTC."""
    interaction_id = fixture["disclosure_id"]
    if not aid_enabled() and not feature_enabled("HG_AID_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "interaction_id": interaction_id,
            "permission_granted": False,
            "aid_enabled": False,
        }

    drafts: list[dict[str, Any]] = []
    capability_claim = fixture.get("capability_claim", "")
    evidence_ref = fixture.get("capability_evidence_ref") or None
    limit_result = evaluate_capability_limit(
        interaction_id=interaction_id,
        capability_claim=capability_claim,
        evidence_ref=evidence_ref,
        observed_at=observed_at,
    )

    if isinstance(limit_result, dict) and limit_result.get("status") == "refused":
        reason = str(limit_result.get("reason_code", REFUSED_UNPROVEN_CAPABILITY))
        drafts.append(bridge.signal_refused(interaction_id=interaction_id, reason_code=reason))
        emitted = emit_drafts(bus, drafts, source="aid.service") if aid_enabled() else []
        return {
            "status": "refused",
            "interaction_id": interaction_id,
            "permission_granted": False,
            "authority_created": False,
            "reason_code": reason,
            "draft_count": len(drafts),
            "emitted_count": len(emitted),
            "aid_enabled": aid_enabled(),
        }

    disclosure = build_disclosure_card(fixture, observed_at=observed_at)
    mode_card = build_mode_card(fixture, observed_at=observed_at)
    uncertainty = assemble_uncertainty(
        interaction_id,
        trl_feed=trl_feed,
        sab_feed=sab_feed,
        fixture=fixture,
        observed_at=observed_at,
    )
    generated = assemble_generated_content(interaction_id, syn_feed=syn_feed, fixture=fixture, observed_at=observed_at)
    policy_eval = evaluate_disclosure_policy(disclosure)
    routing = route_advisory(disclosure, syn_feed=syn_feed, trl_feed=trl_feed, sab_feed=sab_feed)
    missing = detect_missing_disclosure(interaction_id=interaction_id, disclosure=disclosure)

    limit_card: CapabilityLimitCard | None = limit_result if isinstance(limit_result, CapabilityLimitCard) else None

    drafts.append(
        bridge.disclosure_created(
            disclosure_id=disclosure.disclosure_id,
            record_hash=disclosure.record_hash,
            runtime_mode=disclosure.runtime_mode,
        )
    )
    drafts.append(
        bridge.mode_card_recorded(
            mode_card_id=mode_card.mode_card_id,
            interaction_id=interaction_id,
            record_hash=mode_card.record_hash,
        )
    )
    if limit_card:
        drafts.append(
            bridge.capability_limits_recorded(
                limit_card_id=limit_card.limit_card_id,
                interaction_id=interaction_id,
                status=limit_card.status,
            )
        )
    drafts.append(
        bridge.uncertainty_disclosed(
            uncertainty_id=uncertainty.uncertainty_id,
            interaction_id=interaction_id,
            trl_feed_status=uncertainty.trl_feed_status,
            sab_feed_status=uncertainty.sab_feed_status,
        )
    )
    drafts.append(
        bridge.generated_content_disclosed(
            content_disclosure_id=generated.content_disclosure_id,
            interaction_id=interaction_id,
            syn_feed_status=generated.syn_feed_status,
            syn_artifact_id=generated.syn_artifact_id,
        )
    )
    if syn_feed is None:
        drafts.append(
            bridge.operator_education_recommended(
                interaction_id=interaction_id,
                reason="syn_feed_absent",
            )
        )
    if trl_feed is None or sab_feed is None:
        drafts.append(
            bridge.operator_education_recommended(
                interaction_id=interaction_id,
                reason="trl_sab_feed_absent",
            )
        )

    emitted = emit_drafts(bus, drafts, source="aid.service") if aid_enabled() else []

    return {
        "status": "recorded",
        "interaction_id": interaction_id,
        "permission_granted": False,
        "authority_created": False,
        "disclosure": disclosure.to_payload(),
        "mode_card": mode_card.to_payload(),
        "limit_card": limit_card.to_payload() if limit_card else None,
        "uncertainty": uncertainty.to_payload(),
        "generated_content": generated.to_payload(),
        "policy_eval": policy_eval,
        "routing": routing,
        "missing_check": missing,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "aid_enabled": aid_enabled(),
    }


__all__ = ["FIXTURE", "FIXTURE_CLOCK", "process_disclosure"]
