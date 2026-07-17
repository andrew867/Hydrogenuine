"""Build telemetry snapshot from collector state and probes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.openvino_watchtower.schema import (
    DeviceStatus,
    FreshnessVerdict,
    ModelStatus,
    ProviderStatus,
    TelemetryFreshness,
    TelemetryRedactionPolicy,
    TelemetrySnapshot,
    new_snapshot_id,
)

WARNING_MS = 30_000.0
STALE_MS = 120_000.0
CONTACT_LOST_MS = 300_000.0


def compute_freshness(
    generated_at: str | None,
    *,
    now: datetime | None = None,
    last_event_at: str | None = None,
) -> TelemetryFreshness:
    now = now or datetime.now(timezone.utc)
    ref = generated_at or last_event_at
    if not ref:
        return TelemetryFreshness(
            generated_at=now.isoformat(),
            freshness_age_ms=CONTACT_LOST_MS + 1,
            freshness_verdict="contact_lost",
            warning_threshold_ms=WARNING_MS,
            stale_threshold_ms=STALE_MS,
            contact_lost_threshold_ms=CONTACT_LOST_MS,
        )
    try:
        ts = datetime.fromisoformat(ref.replace("Z", "+00:00"))
    except ValueError:
        return TelemetryFreshness(
            generated_at=now.isoformat(),
            freshness_age_ms=CONTACT_LOST_MS + 1,
            freshness_verdict="contact_lost",
        )
    age_ms = max(0.0, (now - ts).total_seconds() * 1000.0)
    if age_ms >= CONTACT_LOST_MS:
        verdict: FreshnessVerdict = "contact_lost"
    elif age_ms >= STALE_MS:
        verdict = "stale"
    elif age_ms >= WARNING_MS:
        verdict = "warning"
    else:
        verdict = "fresh"
    return TelemetryFreshness(
        generated_at=ref,
        freshness_age_ms=round(age_ms, 1),
        freshness_verdict=verdict,
        warning_threshold_ms=WARNING_MS,
        stale_threshold_ms=STALE_MS,
        contact_lost_threshold_ms=CONTACT_LOST_MS,
    )


def panel_state_for_snapshot(snapshot: dict[str, Any]) -> str:
    verdict = str(snapshot.get("freshness_verdict", "contact_lost"))
    provider = snapshot.get("provider_status") or {}
    if verdict in {"stale", "contact_lost"}:
        return "YELLOW" if verdict == "stale" else "RED"
    if not provider.get("healthy") and provider.get("mode") == "unavailable":
        return "YELLOW"
    if snapshot.get("error_count", 0) > 0 and snapshot.get("active_inference_spans"):
        return "YELLOW"
    if provider.get("healthy"):
        return "GREEN"
    if provider.get("mode") == "fixture":
        return "YELLOW"
    return "YELLOW"


def build_snapshot_dict(collector_state: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    generated_at = collector_state.get("last_updated") or now.isoformat()
    freshness = compute_freshness(generated_at, now=now, last_event_at=collector_state.get("last_event_at"))

    provider_raw = collector_state.get("provider_status") or {}
    provider = ProviderStatus(**provider_raw) if isinstance(provider_raw, dict) else provider_raw

    model_raw = collector_state.get("model_status") or {}
    model = ModelStatus(**model_raw) if isinstance(model_raw, dict) else model_raw

    device_raw = collector_state.get("device_status") or {}
    device = DeviceStatus(**device_raw) if isinstance(device_raw, dict) else device_raw

    snap = TelemetrySnapshot(
        generated_at=generated_at,
        snapshot_id=collector_state.get("snapshot_id") or new_snapshot_id(),
        freshness_age_ms=freshness.freshness_age_ms,
        freshness_verdict=freshness.freshness_verdict,
        provider_status=provider,
        openvino_status=dict(collector_state.get("openvino_status") or {}),
        model_status=model,
        device_status=device,
        active_inference_spans=list(collector_state.get("active_inference_spans") or []),
        recent_inference_spans=list(collector_state.get("recent_inference_spans") or []),
        organ_activity=dict(collector_state.get("organ_activity") or {}),
        queue_depths=dict(collector_state.get("queue_depths") or {}),
        gpu_metrics=dict(collector_state.get("gpu_metrics") or {}),
        process_metrics=dict(collector_state.get("process_metrics") or {}),
        error_summary=dict(collector_state.get("error_summary") or {}),
        receipt_refs=list(collector_state.get("receipt_refs") or []),
        proof_refs=list(collector_state.get("proof_refs") or []),
        redaction=collector_state.get("redaction") or TelemetryRedactionPolicy(),
        request_count=int(collector_state.get("request_count") or 0),
        error_count=int(collector_state.get("error_count") or 0),
        rolling_latency_ms=collector_state.get("rolling_latency_ms"),
    )
    data = snap.to_dict()
    data["panel_state"] = panel_state_for_snapshot(data)
    data["safe_to_step_away"] = (
        data["panel_state"] == "GREEN"
        and not data["active_inference_spans"]
        and data["freshness_verdict"] == "fresh"
    )
    return data


__all__ = [
    "CONTACT_LOST_MS",
    "STALE_MS",
    "WARNING_MS",
    "build_snapshot_dict",
    "compute_freshness",
    "panel_state_for_snapshot",
]
