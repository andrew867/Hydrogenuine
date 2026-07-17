"""REB evaluator — re-entry is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.reb_cluster.errors import (
    REFUSED_REENTRY_PACKET_AS_PERMISSION,
    REB_REENTRY_REQUEST_RECORDED,
    RebValidationError,
)
from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.audit import audit_discontinuity_events
from hg_runtime.reentry_boundary.events import adversarial_selection_event, decision_selection_event
from hg_runtime.reentry_boundary.fixtures import bundle_from_parts, load_fixture_bundles
from hg_runtime.reentry_boundary.proposal import dispatch_authority_chain_proposal
from hg_runtime.reentry_boundary.queue import FakeReEntryQueue
from hg_runtime.reentry_boundary.router import refuse_reb_as_authority, route_reentry_request
from hg_runtime.reentry_boundary.types import (
    FIXTURE_CLOCK,
    ReEntryDecision,
    ReEntryPacket,
    ReEntryRequest,
    discontinuity_from_fixture,
    reentry_request_from_fixture,
)


def record_reentry_request(
    reentry_request: ReEntryRequest,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_reb_as_authority(treat_as_authority=True)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": REB_REENTRY_REQUEST_RECORDED,
        "reentry_request": reentry_request.to_payload(),
        "permission_granted": False,
        "emitted_events": ("REB_REENTRY_REQUEST_RECORDED",),
    }


def route_reentry_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    discontinuity, reentry_request, notes = bundle_from_parts(bundle)
    recorded = record_reentry_request(reentry_request)
    routed = route_reentry_request(
        discontinuity,
        reentry_request,
        notes=notes,
        tim_fresh=bool(bundle.get("tim_fresh", False)),
        adversarial_signal=bundle.get("adversarial_signal"),
        bundle=bundle,
        observed_at=observed_at,
    )
    if routed.get("status") == "contained":
        return {
            **advisory_only_marker(),
            "status": "contained",
            "bundle_id": bundle.get("bundle_id"),
            "recorded_request": recorded,
            "route": routed,
            "permission_granted": False,
        }

    decision_payload = routed.get("reentry_decision")
    packet_payload = routed.get("reentry_packet")
    proposal = None
    if isinstance(decision_payload, dict) and isinstance(packet_payload, dict):
        decision = _decision_from_payload(decision_payload)
        packet = _packet_from_payload(packet_payload)
        proposal = dispatch_authority_chain_proposal(reentry_request, decision, packet)

    decision_class = decision_payload.get("decision") if isinstance(decision_payload, dict) else None
    adversarial = bundle.get("adversarial_signal")
    events = ["REB_DISCONTINUITY_EVENT_RECORDED", "REB_TEMPORAL_CONTINUITY_ASSESSMENT_CREATED", "REB_LONG_GAP_POLICY_APPLIED"]
    if adversarial:
        events.append(adversarial_selection_event(str(adversarial)))
    if decision_class:
        events.append(decision_selection_event(decision_class))  # type: ignore[arg-type]
    events.append("REB_REENTRY_PACKET_CREATED")

    return {
        **advisory_only_marker(),
        "status": routed.get("status"),
        "bundle_id": bundle.get("bundle_id"),
        "recorded_request": recorded,
        "route": routed,
        "authority_chain_proposal": proposal,
        "permission_granted": False,
        "external_action_taken": False,
        "emitted_events": tuple(events),
    }


def _decision_from_payload(payload: dict[str, Any]) -> ReEntryDecision:
    return ReEntryDecision(
        reentry_decision_id=str(payload["reentry_decision_id"]),
        reentry_request_ref=str(payload["reentry_request_ref"]),
        assessment_ref=str(payload["assessment_ref"]),
        decision=payload["decision"],  # type: ignore[arg-type]
        reason=str(payload["reason"]),
        allowed_effects=tuple(payload.get("allowed_effects", ())),
        forbidden_effects=tuple(payload.get("forbidden_effects", ())),
        required_next_refs=tuple(payload.get("required_next_refs", ())),
    )


def _packet_from_payload(payload: dict[str, Any]) -> ReEntryPacket:
    return ReEntryPacket(
        packet_id=str(payload["packet_id"]),
        agent_ref=str(payload["agent_ref"]),
        discontinuity_event_ref=str(payload["discontinuity_event_ref"]),
        assessment_ref=str(payload["assessment_ref"]),
        decision_ref=str(payload["decision_ref"]),
        operator_visible_summary=str(payload["operator_visible_summary"]),
        stale_context_summary=str(payload["stale_context_summary"]),
        fresh_context_summary=str(payload["fresh_context_summary"]),
        required_disclosures=tuple(payload.get("required_disclosures", ())),
        allowed_next_actions=tuple(payload.get("allowed_next_actions", ())),
        forbidden_next_actions=tuple(payload.get("forbidden_next_actions", ())),
        required_reviews=tuple(payload.get("required_reviews", ())),
        expires_at=payload.get("expires_at"),
    )


def analyze_fixture_bundles(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    active = bundles if bundles is not None else load_fixture_bundles()
    results: list[dict[str, object]] = []
    for bundle in active:
        results.append(route_reentry_bundle(bundle, observed_at=observed_at))
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "reb.advisory.fixture_bundles_analyzed",
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "permission_granted": False,
    }


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for row in fixtures:
        result = route_reentry_bundle(row, observed_at=observed_at)
        results.append(result)
        route = result.get("route", {})
        if isinstance(route, dict):
            packet = route.get("reentry_packet")
            if isinstance(packet, dict):
                hashes.append(str(packet.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def enqueue_fixture_queue(
    bundles: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, object]:
    queue = FakeReEntryQueue()
    active = bundles if bundles is not None else load_fixture_bundles()
    enqueued: list[dict[str, object]] = []
    for bundle in active[:3]:
        _, reentry_request, _ = bundle_from_parts(bundle)
        enqueued.append(queue.enqueue(reentry_request))
    return {
        **advisory_only_marker(),
        "status": "queued",
        "fake_queue_only": True,
        "queue_depth": queue.depth,
        "enqueued": enqueued,
        "permission_granted": False,
    }


def refuse_reentry_packet_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RebValidationError(
            REFUSED_REENTRY_PACKET_AS_PERMISSION,
            "re-entry packet is not permission",
        )


__all__ = [
    "analyze_fixture_bundles",
    "audit_discontinuity_events",
    "enqueue_fixture_queue",
    "record_reentry_request",
    "refuse_reentry_packet_as_permission",
    "replay_fixture_stream",
    "route_reentry_bundle",
]
