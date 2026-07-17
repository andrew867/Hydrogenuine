"""Operator registry loader — hash-anchored, file-backed (CT-01)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from hg_core.iam.types import AUTHORITY_SCOPES, AGENT_ZERO_ID, OperatorRecord, OperatorRegistry

_REGISTRY_CACHE: OperatorRegistry | None = None


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_registry_path() -> Path:
    return workspace_root() / "config" / "operator_registry_v1.yaml"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_registry_hash(payload: dict[str, Any]) -> str:
    from hg_srp.apply_types import content_hash

    body = {k: v for k, v in payload.items() if k != "registry_hash"}
    return content_hash({"registry": body})


def _parse_operator(raw: dict[str, Any]) -> OperatorRecord:
    scopes = tuple(str(s) for s in raw.get("authority_scopes") or [])
    for scope in scopes:
        if scope not in AUTHORITY_SCOPES:
            raise ValueError(f"unknown_authority_scope:{scope}")
    if raw.get("operator_id") == AGENT_ZERO_ID:
        raise ValueError("agent_zero_cannot_be_operator")
    if scopes and raw.get("operator_id") == AGENT_ZERO_ID:
        raise ValueError("agent_zero_holds_no_scopes")
    return OperatorRecord(
        operator_id=str(raw["operator_id"]),
        display_name=str(raw.get("display_name") or raw["operator_id"]),
        authority_scopes=scopes,
        key_ref=str(raw.get("key_ref") or ""),
        status=str(raw.get("status") or "active"),
    )


def load_registry(path: Path | None = None, *, use_cache: bool = True) -> OperatorRegistry:
    global _REGISTRY_CACHE
    if use_cache and _REGISTRY_CACHE is not None and path is None:
        return _REGISTRY_CACHE

    reg_path = path or default_registry_path()
    if not reg_path.is_file():
        raise FileNotFoundError(f"operator_registry_missing:{reg_path}")

    raw = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("operator_registry_invalid")

    schema = str(raw.get("schema") or "")
    if schema != "operator_registry_v1":
        raise ValueError(f"operator_registry_schema_mismatch:{schema}")

    operators = tuple(_parse_operator(item) for item in raw.get("operators") or [])
    legacy_aliases = {str(k): str(v) for k, v in (raw.get("legacy_aliases") or {}).items()}
    mode = str(raw.get("mode") or "")
    tenant_id = str(raw.get("tenant_id") or "default")

    if mode == "local_single_user":
        active = [op for op in operators if op.status == "active"]
        if len(active) != 1:
            raise ValueError("local_single_user_requires_exactly_one_active_operator")

    payload = {
        "schema": schema,
        "schema_version": str(raw.get("schema_version") or "1.0"),
        "mode": mode,
        "tenant_id": tenant_id,
        "operators": [op.to_payload() for op in operators],
        "legacy_aliases": dict(sorted(legacy_aliases.items())),
    }
    registry_hash = compute_registry_hash(payload)

    registry = OperatorRegistry(
        schema=schema,
        schema_version=str(raw.get("schema_version") or "1.0"),
        mode=mode,
        tenant_id=tenant_id,
        operators=operators,
        legacy_aliases=legacy_aliases,
        registry_hash=registry_hash,
        source_path=str(reg_path),
    )
    if use_cache and path is None:
        _REGISTRY_CACHE = registry
    return registry


def clear_registry_cache() -> None:
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None


def resolve_operator_id(actor: str, registry: OperatorRegistry | None = None) -> str | None:
    """Resolve actor to canonical operator_id via registry or legacy alias."""
    if not actor or not str(actor).strip():
        return None
    actor = str(actor).strip()
    if actor == AGENT_ZERO_ID or actor.startswith("agent:"):
        return None

    reg = registry or load_registry()
    if actor in reg.legacy_aliases:
        return reg.legacy_aliases[actor]

    for op in reg.operators:
        if op.operator_id == actor:
            return op.operator_id
    return None


def get_operator(operator_id: str, registry: OperatorRegistry | None = None) -> OperatorRecord | None:
    reg = registry or load_registry()
    for op in reg.operators:
        if op.operator_id == operator_id:
            return op
    return None


def operator_has_scope(operator_id: str, scope: str, registry: OperatorRegistry | None = None) -> bool:
    if scope not in AUTHORITY_SCOPES:
        return False
    op = get_operator(operator_id, registry=registry)
    if op is None or op.status != "active":
        return False
    return scope in op.authority_scopes


__all__ = [
    "clear_registry_cache",
    "compute_registry_hash",
    "default_registry_path",
    "get_operator",
    "load_registry",
    "operator_has_scope",
    "resolve_operator_id",
    "workspace_root",
]
