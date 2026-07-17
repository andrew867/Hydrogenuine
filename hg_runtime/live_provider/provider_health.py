"""Provider health probing — no generation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from hg_runtime.live_provider.local_provider_clients import probe_http_endpoint
from hg_runtime.live_provider.provider_identity import (
    build_model_identity,
    build_provider_identity,
    provider_configured,
    unavailable_verdict_for_kind,
)
from hg_runtime.live_provider.schema import (
    LiveProviderVerdict,
    ProviderHealthReceipt,
    ProviderRuntimeMode,
    load_live_provider_policy,
    new_id,
    now_iso,
)

WORKSPACE = Path(__file__).resolve().parents[2]
HEALTH_DIR = Path(".hg-local/agent_zero/live_provider/health")


def _health_store_path() -> Path:
    root = WORKSPACE / HEALTH_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_health_receipt(receipt: ProviderHealthReceipt) -> Path:
    path = _health_store_path() / f"{receipt.health_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2), encoding="utf-8")
    return path


def load_latest_health_receipt(provider_ref: str | None = None) -> ProviderHealthReceipt | None:
    root = _health_store_path()
    if not root.is_dir():
        return None
    files = sorted(root.glob("*.json"), reverse=True)
    for fp in files:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if provider_ref and data.get("provider_ref") != provider_ref:
            continue
        return ProviderHealthReceipt(
            health_receipt_id=data["health_receipt_id"],
            provider_ref=data["provider_ref"],
            model_ref=data.get("model_ref"),
            checked_at=data["checked_at"],
            available=data["available"],
            latency_ms=data.get("latency_ms"),
            context_length=data.get("context_length"),
            tokens_per_second_estimate=data.get("tokens_per_second_estimate"),
            failure_reason=data.get("failure_reason"),
            verdict=LiveProviderVerdict(data["verdict"]),
            hash=data.get("hash"),
        )
    return None


def probe_provider_health(
    *,
    runtime_mode: ProviderRuntimeMode = ProviderRuntimeMode.DRY_AUTONOMY,
    http_probe=None,
) -> ProviderHealthReceipt:
    """Probe provider health without generating cognitive output."""
    policy = load_live_provider_policy()
    provider = build_provider_identity(runtime_mode=runtime_mode)
    model = build_model_identity(provider)

    if not provider.provider_id:
        receipt = ProviderHealthReceipt(
            health_receipt_id=new_id("health-rcpt"),
            provider_ref="",
            checked_at=now_iso(),
            available=False,
            verdict=LiveProviderVerdict.RED_PROVIDER_IDENTITY_MISSING,
            failure_reason="missing provider_id",
        ).with_hash()
        store_health_receipt(receipt)
        return receipt

    if not provider_configured(provider):
        verdict = unavailable_verdict_for_kind(provider.provider_kind)
        receipt = ProviderHealthReceipt(
            health_receipt_id=new_id("health-rcpt"),
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            checked_at=now_iso(),
            available=False,
            verdict=verdict,
            failure_reason=f"provider not configured: {provider.provider_kind.value}",
        ).with_hash()
        store_health_receipt(receipt)
        return receipt

    started = time.monotonic()
    probe_fn = http_probe or probe_http_endpoint
    probe_result = probe_fn(provider.endpoint_ref or "")
    latency = int((time.monotonic() - started) * 1000)

    if probe_result.get("available"):
        verdict = LiveProviderVerdict.GREEN_LIVE_PROVIDER_AVAILABLE
        if probe_result.get("degraded"):
            verdict = LiveProviderVerdict.YELLOW_PROVIDER_HEALTH_DEGRADED
        receipt = ProviderHealthReceipt(
            health_receipt_id=new_id("health-rcpt"),
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            checked_at=now_iso(),
            available=True,
            latency_ms=latency,
            context_length=probe_result.get("context_length") or model.context_length,
            tokens_per_second_estimate=probe_result.get("tokens_per_second_estimate"),
            verdict=verdict,
        ).with_hash()
    else:
        receipt = ProviderHealthReceipt(
            health_receipt_id=new_id("health-rcpt"),
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            checked_at=now_iso(),
            available=False,
            latency_ms=latency,
            failure_reason=probe_result.get("failure_reason") or "endpoint unreachable",
            verdict=unavailable_verdict_for_kind(provider.provider_kind),
        ).with_hash()

    if policy.get("provider_receipt_required", True) and not receipt.provider_ref:
        receipt = ProviderHealthReceipt(
            **{**receipt.__dict__, "verdict": LiveProviderVerdict.RED_PROVIDER_IDENTITY_MISSING}
        ).with_hash()

    store_health_receipt(receipt)
    return receipt


def health_status_summary() -> dict[str, Any]:
    provider = build_provider_identity()
    model = build_model_identity(provider)
    receipt = load_latest_health_receipt(provider.provider_id) or probe_provider_health()
    return {
        "provider_kind": provider.provider_kind.value,
        "provider_id": provider.provider_id,
        "model_id": model.model_id,
        "quant_id": model.quant_id,
        "context_length": model.context_length or receipt.context_length,
        "backend": model.backend,
        "device": model.device,
        "available": receipt.available,
        "last_health_check": receipt.checked_at,
        "last_health_receipt": receipt.health_receipt_id,
        "latency_ms": receipt.latency_ms,
        "verdict": receipt.verdict.value,
        "failure_reason": receipt.failure_reason,
    }
