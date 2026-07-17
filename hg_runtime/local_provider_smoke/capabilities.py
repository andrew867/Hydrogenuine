"""Provider capability, inventory, and incompatibility records.

These records describe what a local provider can do and which models it lists. An
incompatibility (e.g. an endpoint that does not expose chat completions, or a GGUF
model assumed loadable by OpenVINO) is recorded honestly, never hidden.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    PROVIDER_CAPABILITY_RECORD_SCHEMA,
    PROVIDER_INCOMPATIBILITY_RECORD_SCHEMA,
    PROVIDER_INVENTORY_RECORD_SCHEMA,
    LocalProviderSmokeError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def record_capability(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("provider_id", "kind"))
    reject_authority_payload(payload)
    record = {
        "schema": PROVIDER_CAPABILITY_RECORD_SCHEMA,
        "provider_id": payload["provider_id"],
        "kind": payload["kind"],
        "supports_models_list": bool(payload.get("supports_models_list", False)),
        "supports_chat_completions": bool(payload.get("supports_chat_completions", False)),
        "supports_load": bool(payload.get("supports_load", False)),
        "supports_unload": bool(payload.get("supports_unload", False)),
        "quirks": list(payload.get("quirks", [])),
        "advisory_only": True,
        **neutral_flags(),
    }
    record["capability_hash"] = canonical_hash(record)
    return record


def record_inventory(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("provider_id",))
    reject_authority_payload(payload)
    models = as_list(payload, "models")
    record = {
        "schema": PROVIDER_INVENTORY_RECORD_SCHEMA,
        "provider_id": payload["provider_id"],
        "models": list(models),
        "model_count": len(models),
        "source": payload.get("source", "endpoint_models_list"),
        "advisory_only": True,
        **neutral_flags(),
    }
    record["inventory_hash"] = canonical_hash(record)
    return record


def record_incompatibility(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("provider_id", "reason"))
    reject_authority_payload(payload)
    record = {
        "schema": PROVIDER_INCOMPATIBILITY_RECORD_SCHEMA,
        "provider_id": payload["provider_id"],
        "reason": payload["reason"],
        "detail": payload.get("detail", ""),
        "hidden": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    record["incompatibility_hash"] = canonical_hash(record)
    return record


def reject_openvino_gguf_assumption(*, provider_kind: str, model_id: str, control=None) -> dict[str, Any]:
    """OpenVINO must not be assumed to load a GGUF model downloaded for LM Studio."""
    preempt_if_needed(control)
    is_openvino = str(provider_kind).lower() == "openvino"
    looks_gguf = "gguf" in str(model_id).lower()
    if is_openvino and looks_gguf:
        return record_incompatibility(
            {
                "provider_id": "openvino",
                "reason": "openvino_gguf_assumption_rejected",
                "detail": f"GGUF model '{model_id}' is not assumed directly loadable by OpenVINO Model Server",
            },
            control=control,
        )
    raise LocalProviderSmokeError("not_a_gguf_openvino_assumption")


__all__ = [
    "record_capability",
    "record_incompatibility",
    "record_inventory",
    "reject_openvino_gguf_assumption",
]
