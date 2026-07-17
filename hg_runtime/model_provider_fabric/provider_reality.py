"""Provider reality evaluation — no fake cognition."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.infer_live.config import cognitive_soak_active, infer_dry_run_mode
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderFallbackDenied,
    ProviderKind,
    ProviderMode,
    ProviderOutputVerdict,
    ProviderRealityVerdict,
    ProviderReceipt,
    ProviderStatus,
    ProviderUnavailable,
    build_provider_receipt,
    load_provider_reality_policy,
    receipt_counts_as_cognition,
    validate_provider_receipt,
)
from hg_runtime.model_provider_fabric.routing import COGNITIVE_ROLES, route_to_verdict
from hg_runtime.runtime_mode import RuntimeMode, resolve_runtime_mode

WORKSPACE = Path(__file__).resolve().parents[2]


def probe_provider_reality(role: str, runtime_mode: RuntimeMode | None = None) -> ProviderReceipt:
    """Safe provider health probe — no full generation."""
    started = datetime.now(timezone.utc)
    if runtime_mode is None:
        mode_receipt = resolve_runtime_mode()
        runtime_name = mode_receipt.runtime_mode.value
        fixture_mode = mode_receipt.fixture_allowed
    else:
        runtime_name = runtime_mode.value
        fixture_mode = runtime_mode == RuntimeMode.FIXTURE

    verdict, provider_id, provider_mode = route_to_verdict(role, runtime_mode=runtime_mode)
    req_hash = compute_record_hash({"probe": True, "role": role})
    cfg_hash = compute_record_hash(load_provider_reality_policy())

    kind = ProviderKind.LOCAL_OPENVINO
    if provider_mode == ProviderMode.FALLBACK_STUB:
        kind = ProviderKind.STUB
    elif provider_mode == ProviderMode.UNAVAILABLE:
        kind = ProviderKind.UNKNOWN

    status = ProviderStatus.AVAILABLE if verdict == ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE else ProviderStatus.UNAVAILABLE
    if verdict in (ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION, ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION):
        status = ProviderStatus.REFUSED

    ended = datetime.now(timezone.utc)
    latency = int((ended - started).total_seconds() * 1000)

    return build_provider_receipt(
        provider_id=provider_id,
        provider_kind=kind,
        provider_mode=provider_mode,
        role=role,
        request_hash=req_hash,
        config_hash=cfg_hash,
        runtime_mode=runtime_name,
        cognitive_soak_active=cognitive_soak_active(),
        dry_run=infer_dry_run_mode(runtime_mode) or provider_mode == ProviderMode.DRY_RUN,
        fixture_mode=fixture_mode,
        status=status,
        verdict=verdict,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        latency_ms=latency,
    )


def evaluate_provider_output(
    *,
    role: str,
    output_text: str | None,
    receipt: ProviderReceipt | None,
) -> ProviderOutputVerdict:
    """Evaluate whether output counts as honest cognition."""
    policy = load_provider_reality_policy()
    if policy.get("provider_receipt_required", True) and receipt is None:
        return ProviderOutputVerdict.RED_OUTPUT_WITHOUT_RECEIPT

    if receipt is not None:
        val = validate_provider_receipt(receipt)
        if val != receipt.verdict and val.startswith("RED"):
            return ProviderOutputVerdict.RED_OUTPUT_NOT_COGNITION

    if not output_text or not str(output_text).strip():
        return ProviderOutputVerdict.RED_OUTPUT_NOT_COGNITION

    if receipt is None:
        return ProviderOutputVerdict.RED_OUTPUT_WITHOUT_RECEIPT

    if receipt_counts_as_cognition(receipt):
        return ProviderOutputVerdict.GREEN_COGNITIVE_OUTPUT_VALID

    return ProviderOutputVerdict.YELLOW_NON_COGNITIVE_LABELLED


def require_cognitive_receipt(role: str, receipt: ProviderReceipt | None) -> ProviderReceipt:
    """Raise if cognitive role lacks valid live receipt."""
    role_upper = role.strip().upper()
    if role_upper not in COGNITIVE_ROLES:
        if receipt is None:
            raise ProviderUnavailable(
                build_provider_receipt(
                    provider_id="none",
                    provider_kind=ProviderKind.UNKNOWN,
                    provider_mode=ProviderMode.UNAVAILABLE,
                    role=role,
                    request_hash="",
                    config_hash="",
                    runtime_mode="unknown",
                    cognitive_soak_active=False,
                    dry_run=False,
                    fixture_mode=False,
                    status=ProviderStatus.UNAVAILABLE,
                    verdict=ProviderRealityVerdict.RED_PROVIDER_RECEIPT_MISSING,
                )
            )
        return receipt

    if receipt is None:
        raise ProviderUnavailable(probe_provider_reality(role))

    if receipt.verdict == ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION:
        raise ProviderFallbackDenied(receipt)
    if not receipt_counts_as_cognition(receipt):
        raise ProviderUnavailable(receipt)
    return receipt


def label_non_cognitive_output(receipt: ProviderReceipt, output: dict[str, Any]) -> dict[str, Any]:
    """Label output with provider mode — never masquerade as cognition."""
    return {
        **output,
        "provider_receipt_id": receipt.receipt_id,
        "provider_mode": receipt.provider_mode.value,
        "provider_verdict": receipt.verdict.value,
        "counts_as_cognition": receipt_counts_as_cognition(receipt),
        "dry_run": receipt.dry_run,
        "fixture_mode": receipt.fixture_mode,
    }


__all__ = [
    "evaluate_provider_output",
    "label_non_cognitive_output",
    "probe_provider_reality",
    "require_cognitive_receipt",
]
