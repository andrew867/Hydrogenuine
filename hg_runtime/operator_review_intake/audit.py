"""ORI passive review-event audit — slice 2, no live UI."""

from __future__ import annotations

from typing import Any

from hg_core.ori_cluster.errors import ORI_REVIEW_REQUEST_RECORDED
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_review_intake.classifier import classify_review_request
from hg_runtime.operator_review_intake.intake_fixtures import load_static_fixture_requests
from hg_runtime.operator_review_intake.request_types import review_request_from_fixture
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK


def audit_review_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of review-like fixture events — observation only."""
    source_requests = load_static_fixture_requests() if events is None else None
    rows: list[Any] = list(events) if events is not None else list(source_requests or ())
    audited: list[dict[str, object]] = []
    contained_count = 0
    for row in rows:
        if hasattr(row, "review_request_id"):
            request = row
        elif isinstance(row, dict) and "review_request_id" in row:
            request = review_request_from_fixture(row)
        else:
            request = review_request_from_fixture(
                {
                    "review_request_id": str(row.get("event_id", "ori-audit-unknown")),
                    "source_module": str(row.get("source_module", "unknown")),
                    "review_type": str(row.get("review_type", "unknown")),
                    "summary": str(row.get("summary", "audit fixture event")),
                }
            )
        classification = classify_review_request(request)
        if classification.get("status") == "contained":
            contained_count += 1
        audited.append(
            {
                "review_request_id": request.review_request_id,
                "source_module": request.source_module,
                "intake_lane": classification.get("intake_lane"),
                "status": classification.get("status"),
                "record_hash": request.record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": ORI_REVIEW_REQUEST_RECORDED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "contained_count": contained_count,
        "audited_events": audited,
        "live_ui_dispatch": False,
        "permission_granted": False,
    }


__all__ = ["audit_review_events"]
