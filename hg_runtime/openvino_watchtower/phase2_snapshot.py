"""Phase 2 snapshot enrichment."""

from __future__ import annotations

from typing import Any

from hg_runtime.openvino_watchtower.events import read_recent_events
from hg_runtime.openvino_watchtower.index import build_timeline_from_events, read_index
from hg_runtime.openvino_watchtower.incident_export import INCIDENTS_ROOT
from hg_runtime.openvino_watchtower.organ_trace import build_organ_trace, current_blocker
from hg_runtime.openvino_watchtower.performance_budget import evaluate_snapshot
from hg_runtime.openvino_watchtower.session import list_sessions
from hg_runtime.openvino_watchtower.waterfall import build_waterfall


def enrich_snapshot_phase2(snapshot: dict[str, Any], *, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    events = events if events is not None else read_recent_events(limit=500)
    trace = build_organ_trace(events, snapshot=snapshot)
    waterfall = build_waterfall(snapshot, events)
    perf = evaluate_snapshot(snapshot)
    idx = read_index()
    incidents = []
    if INCIDENTS_ROOT.is_dir():
        incidents = sorted([p.name for p in INCIDENTS_ROOT.iterdir() if p.is_dir()], reverse=True)[:5]

    out = dict(snapshot)
    out["phase2"] = {
        "organ_trace": trace,
        "waterfall": waterfall,
        "performance_budget": perf,
        "session_count": idx.get("session_count", 0),
        "replay_session_count": len(list_sessions()),
        "last_incident_id": incidents[0] if incidents else None,
        "current_blocker": current_blocker(trace),
        "standalone_ui_path": "apps/openvino_watchtower/index.html",
        "authority_created": False,
        "permission_granted": False,
    }
    out["performance_verdict"] = perf.get("verdict")
    out["timeline_preview"] = build_timeline_from_events(events)[-20:]
    return out


__all__ = ["enrich_snapshot_phase2"]
