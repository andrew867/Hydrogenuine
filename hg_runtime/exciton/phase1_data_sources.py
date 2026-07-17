"""EXCITON Phase 1 data collectors — social and soak panels."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _degraded, _panel
from hg_runtime.exciton.live_probes import soak_run_status
from hg_runtime.exciton.soak_watchtower import build_soak_watchtower
from hg_runtime.exciton.panel_registry import PHASE_1_REQUIRED_PANELS
from hg_runtime.exciton.schema import ExcitonPanelState, FIXTURE_UTC
from hg_runtime.social_capability.credentials import all_credential_statuses
from hg_runtime.social_capability.draft import load_curated_posts
from hg_runtime.social_capability.read import read_social
from hg_runtime.social_capability.schema import SocialReadRequest, SocialSurface, new_id

WORKSPACE = Path(__file__).resolve().parents[2]
SOCIAL_RECEIPTS = WORKSPACE / ".hg-local" / "social" / "receipts"


def _soak_for_ctx(ctx: CollectorContext) -> dict[str, Any]:
    if ctx.offline_fixture:
        return {"active": False}
    return soak_run_status()


def _live_flags() -> dict[str, Any]:
    env_path = WORKSPACE / ".hg-local/secrets/social.env"
    env: dict[str, str] = dict(os.environ)
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return {
        "live_read_enabled": env.get("HG_SOCIAL_LIVE_READ", "").lower() in ("1", "true", "yes"),
        "live_publish_enabled": env.get("HG_SOCIAL_LIVE_PUBLISH", "").lower() in ("1", "true", "yes"),
        "max_posts": int(env.get("HG_SOCIAL_MAX_POSTS", "0") or "0"),
        "operator_approval_required": env.get("HG_SOCIAL_OPERATOR_APPROVAL_REQUIRED", "true").lower()
        in ("1", "true", "yes"),
    }


def _collect_social_status(ctx: CollectorContext):
    flags = _live_flags()
    creds = [c.to_payload() for c in all_credential_statuses()]
    status_summary = {c["surface"]: c["status"] for c in creds}
    return _panel(
        "SocialStatusPanel",
        ExcitonPanelState.GREEN if not flags["live_publish_enabled"] else ExcitonPanelState.YELLOW,
        {
            "credential_status": status_summary,
            **flags,
            "dm_disabled": True,
            "replies_disabled": True,
        },
    )


def _collect_social_read(ctx: CollectorContext):
    if ctx.offline_fixture:
        return _panel(
            "SocialReadPanel",
            ExcitonPanelState.GREEN,
            {
                "surface": SocialSurface.FIXTURE.value,
                "items_count": 2,
                "trust_disposition": "ALLOW_AS_CARGO",
                "last_read_at": FIXTURE_UTC,
            },
        )
    flags = _live_flags()
    req = SocialReadRequest(new_id("read"), SocialSurface.FIXTURE, live=flags["live_read_enabled"])
    result = read_social(req)
    return _panel(
        "SocialReadPanel",
        ExcitonPanelState.GREEN if result.trust_ok else ExcitonPanelState.YELLOW,
        {
            "surface": result.surface.value,
            "items_count": len(result.items),
            "trust_disposition": result.trust_disposition,
            "last_read_at": result.items[0].retrieved_at if result.items else None,
            "live_read_enabled": flags["live_read_enabled"],
        },
    )


def _collect_social_draft(ctx: CollectorContext):
    curated = load_curated_posts()
    return _panel(
        "SocialDraftPanel",
        ExcitonPanelState.GREEN,
        {
            "draft_id": None,
            "body_preview": "(none — only curated public drafts may publish after operator approval)",
            "confidence": None,
            "trust_ok": True,
            "opb_ok": True,
            "no_authority_claim": True,
            "publishable": False,
            "internal_only": True,
            "curated_posts_available": len(curated),
        },
    )


def _collect_social_queue(ctx: CollectorContext):
    flags = _live_flags()
    pending: list[str] = []
    if SOCIAL_RECEIPTS.exists():
        for path in sorted(SOCIAL_RECEIPTS.glob("*.json"), reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            if str(data.get("decision", "")).upper() in ("QUEUED", "YELLOW_PUBLISH_REQUIRES_OPERATOR"):
                pending.append(data.get("draft_id", path.stem))
            if len(pending) >= 5:
                break
    soak = _soak_for_ctx(ctx)
    if soak.get("active") and not soak.get("publish_enabled"):
        pending.append("soak-observation-window")
    return _panel(
        "SocialApprovalQueuePanel",
        ExcitonPanelState.GREEN,
        {
            "queued_count": len(pending),
            "pending_drafts": pending,
            "operator_approval_required": flags["operator_approval_required"],
            "publish_default": "QUEUE_FOR_OPERATOR",
        },
    )


def _collect_social_receipts(ctx: CollectorContext):
    count = len(list(SOCIAL_RECEIPTS.glob("*.json"))) if SOCIAL_RECEIPTS.exists() else 0
    last_decision = "NONE"
    last_id = None
    if count:
        files = sorted(SOCIAL_RECEIPTS.glob("*.json"), reverse=True)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        last_decision = data.get("decision", "UNKNOWN")
        last_id = data.get("receipt_id")
    run = _soak_for_ctx(ctx)
    run_receipts = run.get("tasks_logged", 0) if run.get("active") else 0
    return _panel(
        "SocialPublishReceiptPanel",
        ExcitonPanelState.GREEN,
        {
            "receipt_count": count,
            "soak_task_receipts": run_receipts,
            "last_decision": last_decision,
            "last_receipt_id": last_id,
        },
    )


def _collect_soak_supervisor(ctx: CollectorContext):
    soak = _soak_for_ctx(ctx)
    wt = build_soak_watchtower() if not ctx.offline_fixture else {}
    if not soak.get("active"):
        return _panel(
            "SoakSupervisorPanel",
            ExcitonPanelState.GREEN,
            {
                "supervisor_state": "IDLE",
                "duration_minutes": 0,
                "elapsed_minutes": 0,
                "verdict": "GREEN_BOUNDED_SOAK_SUPERVISOR_READY",
                "publish_enabled": False,
            },
        )
    publish = soak.get("publish_enabled", False)
    confirmed = soak.get("operator_confirmed", False)
    state = ExcitonPanelState.YELLOW if publish and not confirmed else (
        ExcitonPanelState.YELLOW if publish else ExcitonPanelState.GREEN
    )
    if not soak.get("active"):
        state = ExcitonPanelState.GREEN
    return _panel(
        "SoakSupervisorPanel",
        state,
        {
            "supervisor_state": "RUNNING",
            "duration_minutes": soak.get("duration_minutes", 360),
            "elapsed_minutes": soak.get("elapsed_minutes", 0),
            "remaining_minutes": soak.get("remaining_minutes", 0),
            "observation_minutes": soak.get("observation_minutes", 30),
            "current_phase": soak.get("current_phase", "unknown"),
            "verdict": "GREEN_SOAK_ACTIVE",
            "publish_enabled": publish,
            "operator_confirmed": confirmed,
            "operator_confirmation_required": soak.get("operator_confirmation_required", False),
            "max_posts": soak.get("max_posts", 0),
            "run_dir": soak.get("run_dir"),
            "observer_verdict": soak.get("observer_verdict"),
            "observer_heartbeat_age_seconds": soak.get("observer_heartbeat_age_seconds"),
            "next_cycle_eta_seconds": soak.get("next_cycle_eta_seconds"),
            "data_tier": "LIVE",
        },
    )


def _collect_soak_tasks(ctx: CollectorContext):
    from hg_runtime.bounded_soak.tasks import ALLOWED_TASK_KINDS

    soak = _soak_for_ctx(ctx)
    completed = soak.get("tasks_logged", 0) if soak.get("active") else 0
    return _panel(
        "SoakTaskPanel",
        ExcitonPanelState.GREEN,
        {
            "task_kinds": list(ALLOWED_TASK_KINDS),
            "tasks_completed": completed,
            "tasks_remaining": max(0, len(ALLOWED_TASK_KINDS) - min(completed, len(ALLOWED_TASK_KINDS))),
            "active_cycle_tasks": ["status_check", "social_read_check", "curated_queue"]
            + (["curated_publish"] if soak.get("publish_enabled") else []),
        },
    )


def _collect_soak_timeline(ctx: CollectorContext):
    soak = _soak_for_ctx(ctx)
    events = soak.get("command_events", []) if soak.get("active") else []
    rate = "OK"
    if soak.get("publish_enabled") and soak.get("operator_confirmed"):
        rate = f"max_posts={soak.get('max_posts', 0)}"
    elif soak.get("publish_enabled"):
        rate = "YELLOW_PUBLISH_UNCONFIRMED"
    elif soak.get("active"):
        rate = "observation-no-publish"
    return _panel(
        "SoakTimelinePanel",
        ExcitonPanelState.GREEN if soak.get("active") else ExcitonPanelState.YELLOW,
        {
            "events": events or ["idle"],
            "ewj_refs": ["soak-start", "soak-complete"],
            "rate_limit_status": rate,
            "elapsed_minutes": soak.get("elapsed_minutes", 0),
            "observation_checkpoint": (
                "GREEN_OBSERVATION_READY_FOR_OPERATOR_CONFIRMATION"
                if soak.get("operator_confirmation_required")
                else ("confirmed" if soak.get("operator_confirmed") else "in_progress")
            ),
            "publish_enabled": soak.get("publish_enabled", False),
            "operator_confirmed": soak.get("operator_confirmed", False),
            "phase_restarts": [e for e in events if "PHASE" in e or "CHECKPOINT" in e],
            "data_tier": "LIVE" if soak.get("active") else "LIVE_IDLE",
        },
    )


_PHASE1_COLLECTORS = {
    "SocialStatusPanel": _collect_social_status,
    "SocialReadPanel": _collect_social_read,
    "SocialDraftPanel": _collect_social_draft,
    "SocialApprovalQueuePanel": _collect_social_queue,
    "SocialPublishReceiptPanel": _collect_social_receipts,
    "SoakSupervisorPanel": _collect_soak_supervisor,
    "SoakTaskPanel": _collect_soak_tasks,
    "SoakTimelinePanel": _collect_soak_timeline,
}


def build_phase1_panels(ctx: CollectorContext):
    panels = []
    for panel_id in PHASE_1_REQUIRED_PANELS:
        collector = _PHASE1_COLLECTORS.get(panel_id)
        if collector:
            try:
                panels.append(collector(ctx))
            except Exception as exc:  # noqa: BLE001
                panels.append(_degraded(panel_id, str(exc)[:80]))
        else:
            panels.append(_degraded(panel_id, "collector missing"))
    return panels


__all__ = ["build_phase1_panels"]
