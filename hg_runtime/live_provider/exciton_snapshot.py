"""EXCITON provider monitor snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.live_provider.provider_health import health_status_summary, load_latest_health_receipt
from hg_runtime.live_provider.provider_receipts import load_output_receipt
from hg_runtime.live_provider.provider_receipts import _output_store_path
from hg_runtime.live_provider.schema import LiveProviderVerdict


def _freshness(checked_at: str | None, *, max_stale_seconds: int = 180) -> str:
    if not checked_at:
        return "missing"
    try:
        ts = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > max_stale_seconds:
            return "stale"
        return "fresh"
    except ValueError:
        return "unknown"


def build_provider_monitor_fields() -> dict[str, Any]:
    summary = health_status_summary()
    health = load_latest_health_receipt(summary.get("provider_id"))
    last_output = None
    root = _output_store_path()
    if root.is_dir():
        files = sorted(root.glob("*.json"), reverse=True)
        if files:
            import json

            data = json.loads(files[0].read_text(encoding="utf-8"))
            last_output = data.get("provider_output_receipt_id")

    freshness = _freshness(summary.get("last_health_check"))
    verdict = summary.get("verdict", LiveProviderVerdict.YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED.value)
    if freshness == "missing":
        verdict = LiveProviderVerdict.RED_PROVIDER_HEALTH_FAKE_GREEN.value.replace("FAKE_GREEN", "MISSING")
    elif freshness == "stale":
        verdict = LiveProviderVerdict.YELLOW_PROVIDER_HEALTH_DEGRADED.value

    if not health:
        verdict = LiveProviderVerdict.YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED.value

    output_receipt = load_output_receipt(last_output) if last_output else None
    return {
        "panel_title": "Agent Zero Provider Monitor",
        "provider_kind": summary.get("provider_kind"),
        "provider_status": "available" if summary.get("available") else "unavailable",
        "provider_id": summary.get("provider_id"),
        "model_id": summary.get("model_id"),
        "quant_id": summary.get("quant_id"),
        "context_length": summary.get("context_length"),
        "backend": summary.get("backend"),
        "device": summary.get("device"),
        "last_health_check": summary.get("last_health_check"),
        "last_health_receipt": summary.get("last_health_receipt"),
        "last_provider_receipt": last_output,
        "last_latency_ms": summary.get("latency_ms"),
        "json_validity": output_receipt.json_valid if output_receipt else None,
        "schema_validity": output_receipt.schema_valid if output_receipt else None,
        "unavailable_reason": summary.get("failure_reason"),
        "freshness_status": freshness,
        "verdict": verdict,
        "truth_state": verdict,
        "publish_available": False,
        "send_available": False,
        "direct_external_actions_allowed": False,
    }
