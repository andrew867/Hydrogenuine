"""Optional Prometheus metrics exporter for OpenVINO Watchtower."""

from __future__ import annotations

from typing import Any


def render_prometheus_metrics(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []
    req = int(snapshot.get("request_count") or 0)
    err = int(snapshot.get("error_count") or 0)
    active = len(snapshot.get("active_inference_spans") or [])
    model_loaded = 1 if (snapshot.get("model_status") or {}).get("loaded") else 0
    age_s = float(snapshot.get("freshness_age_ms") or 0) / 1000.0
    contact_lost = 1 if snapshot.get("freshness_verdict") == "contact_lost" else 0
    last_dur = 0.0
    recent = snapshot.get("recent_inference_spans") or []
    if recent:
        last_dur = float(recent[0].get("duration_ms") or 0)
    tps = 0.0
    if recent:
        tps = float(recent[0].get("tokens_per_second") or 0)

    def metric(name: str, value: float | int, help_text: str, mtype: str = "gauge") -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {mtype}")
        lines.append(f"{name} {value}")

    metric("hg_openvino_inference_requests_total", req, "Total inference requests observed", "counter")
    metric("hg_openvino_inference_errors_total", err, "Total inference errors observed", "counter")
    metric("hg_openvino_active_inferences", active, "Active inference spans")
    metric("hg_openvino_last_inference_duration_ms", last_dur, "Last completed inference duration ms")
    metric("hg_openvino_tokens_per_second", tps, "Last inference tokens per second")
    metric("hg_openvino_model_loaded", model_loaded, "Model loaded indicator")
    metric("hg_watchtower_snapshot_age_seconds", age_s, "Snapshot freshness age seconds")
    metric("hg_watchtower_contact_lost", contact_lost, "Contact lost indicator")

    for organ_id, payload in (snapshot.get("organ_activity") or {}).items():
        active_flag = 1 if (payload or {}).get("state") == "active" else 0
        lines.append(f'hg_agent_zero_organ_active{{organ="{organ_id}"}} {active_flag}')

    for queue, depth in (snapshot.get("queue_depths") or {}).items():
        lines.append(f'hg_agent_zero_queue_depth{{queue="{queue}"}} {int(depth)}')

    return "\n".join(lines) + "\n"


__all__ = ["render_prometheus_metrics"]
