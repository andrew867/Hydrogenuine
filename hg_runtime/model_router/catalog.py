"""Model catalog entries.

A catalog entry describes a model the router may select. Every entry needs a stable
identity (a content hash or a stable id) so routing and residency records are
replayable. A catalog entry is a description, never a permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.model_router.schemas import (
    MODEL_CATALOG_ENTRY_SCHEMA,
    ModelRouterError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def register_model(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("model_id", "family"))
    data = dict(payload)
    reject_authority_payload(data)
    if not str(data.get("model_hash", "")) and not str(data.get("stable_id", "")):
        raise ModelRouterError("model_catalog_entry_requires_hash_or_stable_id")
    return {
        "schema": MODEL_CATALOG_ENTRY_SCHEMA,
        "model_id": data["model_id"],
        "family": data["family"],
        "model_hash": data.get("model_hash"),
        "stable_id": data.get("stable_id") or data["model_id"],
        "declared_roles": as_list(data, "declared_roles"),
        "context_window": data.get("context_window"),
        "params_billions": data.get("params_billions"),
        "size_mb": data.get("size_mb"),
        "local_only": bool(data.get("local_only", True)),
        **neutral_flags(),
    }


__all__ = ["register_model"]
