"""Provider health simulator — fixture scenarios for debug UI."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from hg_runtime.openvino_watchtower.index import build_timeline_from_events
from hg_runtime.openvino_watchtower.organ_trace import build_organ_trace
from hg_runtime.openvino_watchtower.performance_budget import evaluate_snapshot
from hg_runtime.openvino_watchtower.session import WatchtowerSession
from hg_runtime.openvino_watchtower.snapshot import build_snapshot_dict
from hg_runtime.openvino_watchtower.waterfall import build_waterfall

WORKSPACE = Path(__file__).resolve().parents[2]
SIM_ROOT = WORKSPACE / ".hg-local" / "openvino_watchtower" / "simulator"


SCENARIOS = (
    "idle_provider",
    "model_loading",
    "inference_running",
    "streaming",
    "slow_first_token",
    "inference_failure",
    "openvino_missing",
    "gpu_probe_missing",
    "stale_telemetry",
    "contact_lost",
    "organ_blocked",
    "queue_backlog",
)


def _base_state(scenario: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "last_updated": now,
        "last_event_at": now,
        "provider_status": {
            "provider_id": "sim",
            "mode": "fixture",
            "reachable": scenario != "openvino_missing",
            "healthy": scenario not in {"openvino_missing", "inference_failure", "contact_lost"},
            "openvino_present": scenario != "openvino_missing",
            "runtime_version": "sim-1.0",
            "verdict": "GREEN_SIM" if scenario == "idle_provider" else "YELLOW_SIM",
        },
        "openvino_status": {"present": scenario != "openvino_missing", "verdict": "FIXTURE"},
        "model_status": {
            "model_id": "sim-model",
            "loaded": scenario not in {"model_loading", "openvino_missing"},
            "load_duration_ms": 1200 if scenario == "model_loading" else 800,
            "compile_duration_ms": 600,
        },
        "device_status": {"device": "CPU", "resolved_device": "CPU"},
        "active_inference_spans": [],
        "recent_inference_spans": [],
        "organ_activity": {"model_provider": {"organ_id": "model_provider", "state": "idle", "updated_at": now}},
        "queue_depths": {"operator_queue": 3 if scenario == "queue_backlog" else 0},
        "gpu_metrics": {} if scenario == "gpu_probe_missing" else {"intel_gpu_available": 1.0},
        "process_metrics": {"process_uptime_seconds": 10},
        "error_summary": {},
        "receipt_refs": [],
        "proof_refs": [],
        "request_count": 0,
        "error_count": 1 if scenario == "inference_failure" else 0,
        "rolling_latency_ms": 45000 if scenario == "slow_first_token" else 500,
    }


def _events_for(scenario: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    base = {"ts": now, "authority_created": False, "permission_granted": False}
    if scenario == "streaming":
        return [
            {**base, "event_type": "INFERENCE_STARTED", "organ_id": "WILL", "span_id": "sim-span"},
            {**base, "event_type": "INFERENCE_CHUNK_EMITTED", "span_id": "sim-span", "payload": {"token_count": 4}},
            {**base, "event_type": "INFERENCE_COMPLETED", "span_id": "sim-span"},
        ]
    if scenario == "inference_failure":
        return [{**base, "event_type": "INFERENCE_FAILED", "payload": {"error": "timeout"}}]
    if scenario == "organ_blocked":
        return [{**base, "event_type": "ORGAN_ACTIVITY_UPDATED", "organ_id": "EXCITON", "payload": {"state": "blocked"}}]
    if scenario in {"stale_telemetry", "contact_lost"}:
        return [{**base, "event_type": "TELEMETRY_STALE" if scenario == "stale_telemetry" else "TELEMETRY_CONTACT_LOST"}]
    return [{**base, "event_type": "WATCHTOWER_STARTED", "payload": {"scenario": scenario}}]


def simulate_scenario(scenario: str, *, target_live_dev: bool = False) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    state = _base_state(scenario)
    from hg_runtime.openvino_watchtower.schema import OrganActivityEvent

    state["organ_activity"] = {
        "model_provider": OrganActivityEvent(organ_id="model_provider", state="idle", updated_at=state["last_updated"])
    }
    if scenario in {"inference_running", "streaming", "slow_first_token"}:
        from hg_runtime.openvino_watchtower.schema import InferenceSpan

        span = InferenceSpan(
            span_id=f"sim-{uuid4().hex[:8]}",
            request_id="sim-req",
            organ_id="WILL",
            task=scenario,
            status="active" if scenario != "slow_first_token" else "completed",
            duration_ms=45000 if scenario == "slow_first_token" else 800,
            chunk_count=12 if scenario == "streaming" else 1,
            token_count=48 if scenario == "streaming" else 8,
            tokens_per_second=22.0,
            prompt_hash="abc",
            prompt_length=10,
        )
        if scenario == "slow_first_token":
            state["recent_inference_spans"] = [span]
        else:
            state["active_inference_spans"] = [span]
    if scenario == "organ_blocked":
        state["organ_activity"]["EXCITON"] = OrganActivityEvent(
            organ_id="EXCITON", state="blocked", updated_at=state["last_updated"]
        )
    if scenario == "stale_telemetry":
        state["last_event_at"] = "2020-01-01T00:00:00+00:00"
        state["last_updated"] = "2020-01-01T00:00:00+00:00"
    if scenario == "contact_lost":
        state["last_event_at"] = None
        state["last_updated"] = "2020-01-01T00:00:00+00:00"

    snap = build_snapshot_dict(state)
    snap["data_tier"] = "FIXTURE"
    snap["simulator_scenario"] = scenario
    events = _events_for(scenario)

    root = SIM_ROOT if not target_live_dev else WORKSPACE / ".hg-local/openvino_watchtower/sessions" / f"sim-{scenario}"
    session = WatchtowerSession.open(f"sim-{scenario}-{uuid4().hex[:6]}", root=root.parent if target_live_dev else SIM_ROOT)
    for ev in events:
        session.append_event(ev)
    session.write_snapshot(snap)
    session.write_timeline(build_timeline_from_events(events))
    session.stop()

    return {
        "scenario": scenario,
        "session_id": session.session_id,
        "snapshot": snap,
        "organ_trace": build_organ_trace(events, snapshot=snap),
        "waterfall": build_waterfall(snap, events),
        "performance": evaluate_snapshot(snap),
        "fixture": True,
        "target_live_dev": target_live_dev,
    }


__all__ = ["SCENARIOS", "simulate_scenario"]
