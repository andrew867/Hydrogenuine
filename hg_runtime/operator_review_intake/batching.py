"""ORI deterministic fixture batching — batching is not consent."""

from __future__ import annotations

from hg_core.ori_cluster.errors import ORI_LOW_PRIORITY_DEFERRED, ORI_REVIEW_BATCH_CREATED
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.operator_review_intake.request_types import OperatorReviewBatch, OperatorReviewRequest
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def batch_low_priority_items(
    items: list[dict[str, object]],
    requests: tuple[OperatorReviewRequest, ...],
    *,
    created_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    request_by_id = {r.review_request_id: r for r in requests}
    low_items = [item for item in items if item.get("priority") == "low"]
    if len(low_items) < 2:
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": ORI_LOW_PRIORITY_DEFERRED,
            "batches": [],
            "review_is_advisory_only": True,
        }

    by_source: dict[str, list[str]] = {}
    for item in low_items:
        refs = item.get("request_refs", [])
        if not refs:
            continue
        req = request_by_id.get(str(refs[0]))
        if req is None:
            continue
        by_source.setdefault(req.source_module, []).append(str(item.get("review_item_id", "")))

    batches: list[OperatorReviewBatch] = []
    for source, item_refs in sorted(by_source.items()):
        if len(item_refs) < 2:
            continue
        batches.append(
            OperatorReviewBatch(
                batch_id=_deterministic_id("ori-batch", source, str(len(item_refs))),
                item_refs=tuple(sorted(item_refs)),
                batch_reason="low_priority_digest",
                presentation_mode="digest",
                max_items=len(item_refs),
                created_at=created_at,
            )
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_REVIEW_BATCH_CREATED if batches else ORI_LOW_PRIORITY_DEFERRED,
        "batches": [b.to_payload() for b in batches],
        "critical_never_batched": all(
            item.get("priority") != "critical"
            for item in items
            if any(
                item.get("review_item_id") in b.item_refs
                for b in batches
            )
        ),
        "batching_not_consent": True,
        "review_is_advisory_only": True,
    }


def assign_critical_interrupt_batch(
    items: list[dict[str, object]],
    *,
    created_at: str = FIXTURE_CLOCK,
) -> OperatorReviewBatch | None:
    critical_refs = [
        str(item["review_item_id"])
        for item in items
        if item.get("priority") == "critical" and item.get("review_item_id")
    ]
    if not critical_refs:
        return None
    return OperatorReviewBatch(
        batch_id=_deterministic_id("ori-batch", "critical-interrupt", *critical_refs),
        item_refs=tuple(sorted(critical_refs)),
        batch_reason="urgent_interrupt",
        presentation_mode="interrupt",
        max_items=len(critical_refs),
        created_at=created_at,
    )


__all__ = ["assign_critical_interrupt_batch", "batch_low_priority_items"]
