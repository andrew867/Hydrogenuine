"""ORI evaluator — operator review intake is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.ori_cluster.config import ori_refuse_stale_review
from hg_core.ori_cluster.errors import (
    ORI_EXPIRY_NOT_APPROVAL,
    ORI_REVIEW_ITEM_CREATED,
    ORI_SILENCE_NOT_APPROVAL,
)
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.operator_review_intake.batching import (
    assign_critical_interrupt_batch,
    batch_low_priority_items,
)
from hg_runtime.operator_review_intake.classifier import classify_review_request
from hg_runtime.operator_review_intake.dedupe import deduplicate_review_requests
from hg_runtime.operator_review_intake.events import priority_event
from hg_runtime.operator_review_intake.intake_fixtures import load_static_fixture_requests
from hg_runtime.operator_review_intake.overload import detect_operator_overload
from hg_runtime.operator_review_intake.priority import prioritize_review_requests
from hg_runtime.operator_review_intake.request_types import OperatorReviewRequest, review_request_from_fixture
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK, OperatorReviewReceipt
from hg_runtime.operator_review_intake.validator import evaluate_operator_review_receipt


def _emit_events(*codes: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(codes))


def intake_review_request(
    request: OperatorReviewRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    classification = classify_review_request(request)
    if classification.get("status") == "refused":
        return {
            **classification,
            "emitted_events": _emit_events("ORI_SIGNAL_REFUSED"),
        }
    if classification.get("status") == "contained":
        return {
            **classification,
            "emitted_events": _emit_events(
                "ORI_REVIEW_REQUEST_RECORDED",
                "ORI_AUTHORITY_CONVERSION_CONTAINED",
            ),
        }
    return {
        **classification,
        "emitted_events": _emit_events("ORI_REVIEW_REQUEST_RECORDED"),
        "observed_at": observed_at,
    }


def process_review_queue(
    requests: tuple[OperatorReviewRequest, ...],
    *,
    observed_at: str = FIXTURE_CLOCK,
    window_start: str = FIXTURE_CLOCK,
    window_end: str = "2026-06-14T12:30:00.000000Z",
) -> dict[str, object]:
    classifications = [classify_review_request(r) for r in requests]
    accepted = tuple(
        r
        for r, c in zip(requests, classifications, strict=True)
        if c.get("intake_lane") == "operator_review"
    )

    dedupe = deduplicate_review_requests(accepted)
    canonical_refs = list(dedupe.get("canonical_request_refs", []))
    priority = prioritize_review_requests(accepted, canonical_refs=canonical_refs)
    items = list(priority.get("items", []))

    batching = batch_low_priority_items(items, accepted, created_at=observed_at)
    critical_batch = assign_critical_interrupt_batch(items, created_at=observed_at)
    batches = list(batching.get("batches", []))
    if critical_batch:
        batches.append(critical_batch.to_payload())

    duplicate_count = int(dedupe.get("suppressed_count", 0))
    overload = detect_operator_overload(
        items=items,
        request_count=len(requests),
        duplicate_count=duplicate_count,
        window_start=window_start,
        window_end=window_end,
    )

    events = _emit_events(
        "ORI_REVIEW_REQUEST_RECORDED",
        "ORI_DEDUPLICATION_APPLIED",
    )
    if dedupe.get("dedupe_records"):
        events = events + ("ORI_DUPLICATE_SUPPRESSED",)
    priority_evt = priority_event(str(items[0].get("priority", "normal"))) if items else "ORI_PRIORITY_ASSIGNED"
    events = events + ("ORI_REVIEW_ITEM_CREATED", priority_evt)
    if batches:
        events = events + ("ORI_REVIEW_BATCH_CREATED",)
    if overload.get("overload_signal"):
        events = events + ("ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED",)

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_REVIEW_ITEM_CREATED,
        "classifications": classifications,
        "dedupe": dedupe,
        "priority": priority,
        "batching": {**batching, "batches": batches},
        "overload": overload,
        "items": items,
        "emitted_events": events,
        "observed_at": observed_at,
        "review_is_advisory_only": True,
        "permission_granted": False,
    }


def evaluate_silence_policy(
    request: OperatorReviewRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Silence policies never grant approval."""
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_SILENCE_NOT_APPROVAL,
        "silence_policy": request.silence_policy,
        "approval_implied": False,
        "permission_granted": False,
        "review_request_id": request.review_request_id,
        "emitted_events": _emit_events("ORI_SILENCE_POLICY_APPLIED"),
        "observed_at": observed_at,
    }


def evaluate_expired_review(
    request: OperatorReviewRequest,
    *,
    observed_at: str,
) -> dict[str, object]:
    """Expired reviews do not imply approval."""
    expired = False
    if request.expires_at and ori_refuse_stale_review():
        expired = observed_at >= request.expires_at
    return {
        **advisory_only_marker(),
        "status": "expired" if expired else "recorded",
        "reason_code": ORI_EXPIRY_NOT_APPROVAL if expired else "ori.advisory.not_expired",
        "approval_implied": False,
        "permission_granted": False,
        "review_request_id": request.review_request_id,
        "emitted_events": _emit_events("ORI_REVIEW_EXPIRED") if expired else (),
        "observed_at": observed_at,
    }


def record_operator_response(
    receipt: OperatorReviewReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Record explicit operator response; receipt remains non-authority."""
    evaluated = evaluate_operator_review_receipt(receipt, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": evaluated.get("status", "recorded"),
        "reason_code": evaluated.get("reason_code"),
        "receipt": receipt.to_payload(),
        "evidence_admissible": evaluated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": _emit_events("ORI_OPERATOR_RESPONSE_RECORDED", "ORI_REVIEW_RECEIPT_CREATED"),
        "observed_at": observed_at,
    }


def analyze_fixture_bundle(
    bundle: dict[str, Any] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    if bundle and bundle.get("requests"):
        requests = tuple(review_request_from_fixture(row) for row in bundle["requests"])
    else:
        requests = load_static_fixture_requests()

    queue = process_review_queue(requests, observed_at=observed_at)
    sources = {r.source_module for r in requests}
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "ori.advisory.fixture_bundle_analyzed",
        "fixture_analysis_only": True,
        "review_is_advisory_only": True,
        "source_modules": sorted(sources),
        "queue": queue,
        "all_advisory": queue.get("permission_granted") is False,
        "has_opb": "OPB" in sources,
        "has_ipb": "IPB" in sources,
        "has_arb": "ARB" in sources,
        "has_egi": "EGI" in sources,
    }


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    requests = tuple(review_request_from_fixture(row) for row in fixtures)
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for request in requests:
        result = intake_review_request(request, observed_at=observed_at)
        results.append(result)
        req_payload = result.get("request")
        if isinstance(req_payload, dict):
            hashes.append(str(req_payload.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = [
    "analyze_fixture_bundle",
    "evaluate_expired_review",
    "evaluate_silence_policy",
    "intake_review_request",
    "process_review_queue",
    "record_operator_response",
    "replay_fixture_stream",
]
