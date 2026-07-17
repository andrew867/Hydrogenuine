"""Model memory estimate records and the large-model load policy.

A 30B-class model is load-on-demand only, never default-resident, and never required
for a GREEN smoke. Before any large model load may be planned, a memory estimate is
required and may refuse the load on a 32 GB host.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    MODEL_MEMORY_ESTIMATE_SCHEMA,
    LocalProviderSmokeError,
    classify_model_size,
    is_large_model,
    neutral_flags,
    preempt_if_needed,
    require_fields,
)

DEFAULT_SYSTEM_RAM_GB = 32.0
# Rough per-class resident memory estimates (GB) for a memory check; advisory only.
_CLASS_ESTIMATE_GB = {"tiny": 1.5, "medium": 8.0, "large": 22.0}


def estimate_model_memory(payload: Mapping[str, Any], *, system_ram_gb: float = DEFAULT_SYSTEM_RAM_GB, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("model_id",))
    size_class = classify_model_size(payload["model_id"])
    estimate_gb = float(payload.get("estimate_gb", _CLASS_ESTIMATE_GB.get(size_class, 8.0)))
    fits = estimate_gb <= (system_ram_gb * 0.85)
    record = {
        "schema": MODEL_MEMORY_ESTIMATE_SCHEMA,
        "model_id": payload["model_id"],
        "size_class": size_class,
        "estimate_gb": estimate_gb,
        "system_ram_gb": system_ram_gb,
        "fits_resident": fits,
        "load_on_demand_only": size_class == "large",
        "required_for_green": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    record["estimate_hash"] = canonical_hash(record)
    return record


def require_memory_estimate_before_large_load(model_id: str, memory_estimate: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """A large model load may only be planned after a matching memory estimate exists."""
    if not is_large_model(model_id):
        return memory_estimate or {}
    if not memory_estimate or memory_estimate.get("schema") != MODEL_MEMORY_ESTIMATE_SCHEMA:
        raise LocalProviderSmokeError("model_memory_estimate_required_before_large_load")
    if memory_estimate.get("model_id") != model_id:
        raise LocalProviderSmokeError("model_memory_estimate_required_before_large_load")
    return memory_estimate


__all__ = [
    "DEFAULT_SYSTEM_RAM_GB",
    "estimate_model_memory",
    "require_memory_estimate_before_large_load",
]
