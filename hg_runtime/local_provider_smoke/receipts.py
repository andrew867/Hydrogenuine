"""Load plans, load/unload receipts, and the local-provider smoke receipt.

A real load or unload happens only when the operator has explicitly enabled it; an
unload may only target an instance this smoke loaded, and never an active instance. A
smoke receipt records what happened and is never permission. The dry/live boundary is
enforced: real provider work is impossible without the operator-enabled flags.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.memory import require_memory_estimate_before_large_load
from hg_runtime.local_provider_smoke.schemas import (
    GREEN_LIKE,
    LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA,
    PROVIDER_LOAD_PLAN_SCHEMA,
    PROVIDER_LOAD_RECEIPT_SCHEMA,
    PROVIDER_UNLOAD_RECEIPT_SCHEMA,
    VERDICT_RED_FAILED,
    LocalProviderSmokeError,
    assert_safe_smoke_model,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
)


def build_load_plan(
    *,
    provider_id: str,
    model_id: str,
    memory_estimate: Mapping[str, Any] | None = None,
    allow_large: bool = False,
    control=None,
) -> dict[str, Any]:
    """Plan (not execute) a tiny-model load. Large loads require a memory estimate."""
    preempt_if_needed(control)
    assert_safe_smoke_model(model_id, allow_large=allow_large)
    require_memory_estimate_before_large_load(model_id, memory_estimate)
    plan = {
        "schema": PROVIDER_LOAD_PLAN_SCHEMA,
        "provider_id": provider_id,
        "model_id": model_id,
        "executed": False,
        "real_call": False,
        "memory_estimate_ref": (memory_estimate or {}).get("estimate_hash", ""),
        **neutral_flags(),
    }
    plan["plan_hash"] = canonical_hash(plan)
    return plan


def build_load_receipt(
    *,
    config: Mapping[str, Any],
    provider_id: str,
    model_id: str,
    instance_id: str,
    memory_estimate: Mapping[str, Any] | None = None,
    allow_large: bool = False,
    control=None,
) -> dict[str, Any]:
    """A real load receipt requires operator-enabled real mode + load permission."""
    preempt_if_needed(control)
    if not config.get("enable_real"):
        raise LocalProviderSmokeError("dry_live_boundary_enforced:real_load_requires_operator_enabled")
    if not config.get("allow_load"):
        raise LocalProviderSmokeError("real_load_requires_operator_enabled_flag")
    assert_safe_smoke_model(model_id, allow_large=allow_large)
    require_memory_estimate_before_large_load(model_id, memory_estimate)
    receipt = {
        "schema": PROVIDER_LOAD_RECEIPT_SCHEMA,
        "provider_id": provider_id,
        "model_id": model_id,
        "instance_id": instance_id,
        "owned_by_this_smoke": True,
        "executed": True,
        "real_call": True,
        "is_permission": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def build_unload_receipt(
    *,
    config: Mapping[str, Any],
    provider_id: str,
    instance_id: str,
    owned_instance_ids: list[str],
    active: bool = False,
    control=None,
) -> dict[str, Any]:
    """Unload only an owned, non-active instance, and only when unload is enabled."""
    preempt_if_needed(control)
    if not config.get("enable_real"):
        raise LocalProviderSmokeError("dry_live_boundary_enforced:real_unload_requires_operator_enabled")
    if not config.get("allow_unload"):
        raise LocalProviderSmokeError("real_unload_requires_operator_enabled_flag")
    if instance_id not in (owned_instance_ids or []):
        raise LocalProviderSmokeError("unload_requires_owned_loaded_instance")
    if active:
        raise LocalProviderSmokeError("unload_active_model_rejected")
    receipt = {
        "schema": PROVIDER_UNLOAD_RECEIPT_SCHEMA,
        "provider_id": provider_id,
        "instance_id": instance_id,
        "owned_by_this_smoke": True,
        "active_at_unload": False,
        "executed": True,
        "real_call": True,
        "is_permission": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def build_smoke_receipt(
    *,
    verdict: str,
    lmstudio_status: str,
    openvino_status: str,
    receipt_refs: list[str],
    summary: Mapping[str, Any] | None = None,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    is_green = str(verdict).startswith("GREEN")
    if is_green and not receipt_refs:
        raise LocalProviderSmokeError("missing_receipt_blocks_success")
    receipt = {
        "schema": LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA,
        "verdict": verdict,
        "lmstudio_status": lmstudio_status,
        "openvino_status": openvino_status,
        "receipt_refs": list(receipt_refs),
        "summary": dict(summary or {}),
        "is_permission": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def assert_not_fake_green(*, verdict: str, lmstudio_status: str, openvino_status: str) -> None:
    """A GREEN verdict must match the actual provider statuses."""
    if verdict == "GREEN_LOCAL_PROVIDER_SMOKE_BOTH_PROVIDERS" and not (
        lmstudio_status == "pass" and openvino_status == "pass"
    ):
        raise LocalProviderSmokeError("fake_green_rejected:both_providers_not_passing")
    if verdict == "GREEN_LOCAL_PROVIDER_SMOKE_LMSTUDIO_ONLY_OPENVINO_NOT_CONFIGURED" and not (
        lmstudio_status == "pass" and openvino_status == "not_configured"
    ):
        raise LocalProviderSmokeError("fake_green_rejected:lmstudio_only_claim_mismatch")
    if str(verdict).startswith("GREEN") and (lmstudio_status == "fail" or openvino_status == "fail"):
        raise LocalProviderSmokeError("fake_green_rejected:failing_provider")


def assert_not_permission(record: Mapping[str, Any]) -> Mapping[str, Any]:
    reject_authority_payload(dict(record))
    return record


__all__ = [
    "assert_not_fake_green",
    "assert_not_permission",
    "build_load_plan",
    "build_load_receipt",
    "build_smoke_receipt",
    "build_unload_receipt",
]
