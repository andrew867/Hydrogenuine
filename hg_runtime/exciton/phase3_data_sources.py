"""EXCITON review queue panels — per-item approve/deny before publish."""

from __future__ import annotations

from hg_runtime.exciton.data_sources import CollectorContext, _degraded, _panel
from hg_runtime.exciton.panel_registry import PHASE_3_REQUIRED_PANELS
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.exciton.soak_watchtower import active_soak_run_dir, build_soak_watchtower
from hg_runtime.social_capability.review_policy import unreviewed_publish_path
from hg_runtime.social_capability.review_queue import (
    LEGACY_INCIDENT,
    is_publish_paused,
    load_queue,
    queue_summary,
    review_queue_visible,
)


def _review_fields(run_dir) -> dict:
    if not run_dir:
        return {
            "queued_count": 0,
            "approved_count": 0,
            "denied_count": 0,
            "published_count": 0,
            "live_publish_paused": True,
            "approved_only_mode": False,
            "unreviewed_publish_path": False,
            "legacy_incident_recorded": False,
            "items_summary": [],
            "data_tier": "LIVE",
        }
    summary = queue_summary(run_dir)
    queue = load_queue(run_dir)
    wt = build_soak_watchtower()
    unreviewed = unreviewed_publish_path(
        publish_enabled=bool(wt.get("publish_enabled")),
        live_publish_paused=is_publish_paused(run_dir),
        approved_only_mode=summary.get("approved_only_mode", False),
    )
    items_summary = [
        {
            "queue_item_id": i.queue_item_id,
            "draft_id": i.draft_id,
            "status": i.status.value,
            "sanitized_preview": i.sanitized_preview[:120],
            "incident_class": i.incident_class,
        }
        for i in queue.items[:12]
    ]
    counts = summary.get("counts", {})
    return {
        "queued_count": counts.get("queued", 0),
        "approved_count": counts.get("approved", 0),
        "denied_count": counts.get("denied", 0),
        "published_count": counts.get("published", 0)
        + counts.get("published_legacy_unconfirmed", 0),
        "live_publish_paused": summary.get("live_publish_paused", True),
        "approved_only_mode": summary.get("approved_only_mode", False),
        "unreviewed_publish_path": unreviewed,
        "legacy_incident_recorded": summary.get("legacy_incident_recorded", False),
        "legacy_incident_class": LEGACY_INCIDENT if summary.get("legacy_incident_recorded") else None,
        "items_summary": items_summary,
        "review_queue_visible": review_queue_visible(run_dir),
        "data_tier": "LIVE",
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
    }


def _preview_fields(run_dir) -> dict:
    base = _review_fields(run_dir)
    if not run_dir:
        return {**base, "queue_item_id": None, "draft_hash": None, "status": "idle"}
    queue = load_queue(run_dir)
    target = next((i for i in queue.items if i.status.value == "queued"), None)
    if not target and queue.items:
        target = queue.items[0]
    if not target:
        return {**base, "queue_item_id": None, "status": "empty"}
    return {
        **base,
        "queue_item_id": target.queue_item_id,
        "draft_id": target.draft_id,
        "draft_hash": target.draft_hash,
        "sanitized_preview": target.sanitized_preview,
        "trust_boundary_verdict": target.trust_boundary_verdict,
        "opb_verdict": target.opb_verdict,
        "publish_eligible": target.publish_eligible,
        "status": target.status.value,
        "rate_limit_status": target.rate_limit_status,
    }


def _decision_fields(run_dir) -> dict:
    base = _review_fields(run_dir)
    queue = load_queue(run_dir) if run_dir else None
    selected = None
    if queue:
        selected = next((i for i in queue.items if i.status.value == "queued"), None)
    paused = base.get("live_publish_paused", True)
    a_only = base.get("approved_only_mode", False)
    if paused:
        mode = "paused"
    elif a_only:
        mode = "approved_only"
    else:
        mode = "disabled" if not base.get("unreviewed_publish_path") else "unsafe"
    return {
        **base,
        "selected_queue_item_id": selected.queue_item_id if selected else None,
        "approve_available": bool(selected),
        "deny_available": bool(selected),
        "approve_all_available": False,
        "direct_publish_available": False,
        "live_publish_mode": mode,
        "pause_message": "live publish paused until approved item exists" if paused else None,
    }


def build_phase3_panels(ctx: CollectorContext):
    panels = []
    run_dir = None if ctx.offline_fixture else active_soak_run_dir()
    for panel_id in PHASE_3_REQUIRED_PANELS:
        try:
            if panel_id == "SocialReviewQueuePanel":
                data = _review_fields(run_dir)
                state = ExcitonPanelState.GREEN if data.get("review_queue_visible") else ExcitonPanelState.YELLOW
                if data.get("unreviewed_publish_path"):
                    state = ExcitonPanelState.RED
                panels.append(_panel("SocialReviewQueuePanel", state, data))
            elif panel_id == "SocialDraftPreviewPanel":
                data = _preview_fields(run_dir)
                panels.append(_panel("SocialDraftPreviewPanel", ExcitonPanelState.GREEN, data))
            elif panel_id == "SocialApprovalDecisionPanel":
                data = _decision_fields(run_dir)
                state = ExcitonPanelState.GREEN
                if data.get("approve_all_available") or data.get("direct_publish_available"):
                    state = ExcitonPanelState.RED
                panels.append(_panel("SocialApprovalDecisionPanel", state, data))
            else:
                panels.append(_degraded(panel_id, "collector missing"))
        except Exception as exc:  # noqa: BLE001
            panels.append(_degraded(panel_id, str(exc)[:80]))
    return panels


__all__ = ["build_phase3_panels"]
