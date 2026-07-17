"""EXCITON panel builder for Inference Watchtower."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from hg_runtime.openvino_watchtower.snapshot import panel_state_for_snapshot

WORKSPACE = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = WORKSPACE / ".hg-local" / "openvino_watchtower" / "snapshot.json"


def _fetch_api_snapshot(host: str = "127.0.0.1", port: int | None = None) -> dict[str, Any] | None:
    port = port or default_port()
    url = f"http://{host}:{port}/status"
    try:
        with urlopen(url, timeout=2.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def load_watchtower_snapshot(*, prefer_api: bool = True) -> dict[str, Any]:
    if prefer_api:
        live = _fetch_api_snapshot()
        if live:
            return live
    if SNAPSHOT_PATH.is_file():
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "freshness_verdict": "contact_lost",
        "provider_status": {"mode": "unavailable", "healthy": False, "verdict": "YELLOW_PROVIDER_UNREACHABLE"},
        "active_inference_spans": [],
        "organ_activity": {},
        "redaction": {"raw_prompts_enabled": False, "hidden_chain_of_thought_enabled": False},
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
        "panel_state": "RED",
        "human_message": "Watchtower contact lost — stale snapshot unavailable.",
    }


def exciton_panel_fields(snapshot: dict[str, Any]) -> dict[str, Any]:
    provider = snapshot.get("provider_status") or {}
    model = snapshot.get("model_status") or {}
    device = snapshot.get("device_status") or {}
    active = snapshot.get("active_inference_spans") or []
    first_active = active[0] if active else {}
    phase2 = snapshot.get("phase2") or {}
    return {
        "data_tier": "LIVE" if snapshot.get("freshness_verdict") == "fresh" else "DEGRADED",
        "provider_status": provider.get("verdict"),
        "provider_mode": provider.get("mode"),
        "openvino_present": provider.get("openvino_present"),
        "openvino_runtime_version": provider.get("runtime_version"),
        "model_id": model.get("model_id"),
        "model_loaded": model.get("loaded"),
        "device": device.get("resolved_device") or device.get("device"),
        "active_inference_count": len(active),
        "active_organ": first_active.get("organ_id"),
        "active_task": first_active.get("task"),
        "elapsed_ms": first_active.get("duration_ms"),
        "chunk_count": first_active.get("chunk_count"),
        "token_count": first_active.get("token_count"),
        "tokens_per_second": first_active.get("tokens_per_second"),
        "queue_depths": snapshot.get("queue_depths"),
        "organ_activity_summary": {
            k: (v.get("state") if isinstance(v, dict) else getattr(v, "state", "idle"))
            for k, v in (snapshot.get("organ_activity") or {}).items()
        },
        "freshness_verdict": snapshot.get("freshness_verdict"),
        "freshness_age_ms": snapshot.get("freshness_age_ms"),
        "request_count": snapshot.get("request_count"),
        "error_count": snapshot.get("error_count"),
        "rolling_latency_ms": snapshot.get("rolling_latency_ms"),
        "process_metrics": snapshot.get("process_metrics"),
        "gpu_metrics": snapshot.get("gpu_metrics"),
        "performance_verdict": snapshot.get("performance_verdict") or phase2.get("performance_budget", {}).get("verdict"),
        "replay_session_count": phase2.get("replay_session_count", 0),
        "last_incident_id": phase2.get("last_incident_id"),
        "current_blocker": phase2.get("current_blocker"),
        "watchtower_standalone_path": phase2.get("standalone_ui_path", "apps/openvino_watchtower/index.html"),
        "organ_trace_verdict": (phase2.get("organ_trace") or {}).get("verdict"),
        "redaction_active": True,
        "raw_prompt_disabled": not (snapshot.get("redaction") or {}).get("raw_prompts_enabled", False),
        "hidden_cot_disabled": not (snapshot.get("redaction") or {}).get("hidden_chain_of_thought_enabled", False),
        "safe_to_step_away": snapshot.get("safe_to_step_away", False),
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
    }


def exciton_panel_state(snapshot: dict[str, Any]):
    from hg_runtime.exciton.schema import ExcitonPanelState

    ps = panel_state_for_snapshot(snapshot)
    if ps == "GREEN":
        return ExcitonPanelState.GREEN
    if ps == "RED":
        return ExcitonPanelState.RED
    return ExcitonPanelState.YELLOW


__all__ = [
    "exciton_panel_fields",
    "exciton_panel_state",
    "load_watchtower_snapshot",
]
