"""ORI operator-visible digest fixture — slice 3, digest is not approval."""

from __future__ import annotations

from hg_core.ori_cluster.errors import ORI_LOW_PRIORITY_DEFERRED
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_review_intake.evaluator import process_review_queue
from hg_runtime.operator_review_intake.intake_fixtures import load_static_fixture_requests
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK


def render_operator_digest_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Build operator-visible digest from batched low-priority fixture items."""
    requests = load_static_fixture_requests()
    queue = process_review_queue(requests, observed_at=observed_at)
    batching = queue.get("batching", {})
    batches = batching.get("batches", []) if isinstance(batching, dict) else []
    digest_batches = []
    for b in batches:
        mode = b.presentation_mode if hasattr(b, "presentation_mode") else b.get("presentation_mode")
        if mode == "digest":
            digest_batches.append(b.to_payload() if hasattr(b, "to_payload") else b)
    digest_items: list[dict[str, object]] = []
    for batch in digest_batches:
        item_refs = batch.get("item_refs", ()) if isinstance(batch, dict) else batch.item_refs
        for item_ref in item_refs:
            digest_items.append(
                {
                    "item_ref": item_ref,
                    "presentation_mode": "digest",
                    "digest_is_not_approval": True,
                    "permission_granted": False,
                }
            )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_LOW_PRIORITY_DEFERRED,
        "digest_fixture_only": True,
        "digest_is_not_approval": True,
        "observed_at": observed_at,
        "digest_batch_count": len(digest_batches),
        "digest_item_count": len(digest_items),
        "digest_items": digest_items,
        "live_approval_effect": False,
        "permission_granted": False,
    }


__all__ = ["render_operator_digest_fixture"]
