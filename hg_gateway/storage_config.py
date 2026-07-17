"""Shared gateway storage configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def gateway_store_backend(default: str = "sqlite") -> str:
    return (os.environ.get("HG_GATEWAY_STORE") or default).strip().lower()


def gateway_db_path(default: str = "./memory/gateway.sqlite3") -> str:
    return str(Path(os.environ.get("HG_GATEWAY_DB_PATH", default)).expanduser())


def gateway_postgres_dsn(required: bool = False) -> str:
    dsn = (os.environ.get("HG_GATEWAY_POSTGRES_DSN") or "").strip()
    if required and not dsn:
        raise RuntimeError("HG_GATEWAY_POSTGRES_DSN is required when HG_GATEWAY_STORE=postgres")
    return dsn


def gateway_requires_postgres() -> bool:
    return _truthy(os.environ.get("HG_GATEWAY_REQUIRE_POSTGRES"))


def _workspace_memory_path() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return (get_workspace_root().resolve() / "memory").resolve()
    except Exception:
        return None


def gateway_db_path_is_workspace_memory() -> bool:
    workspace_memory = _workspace_memory_path()
    if workspace_memory is None:
        return False
    try:
        return Path(gateway_db_path()).expanduser().resolve().is_relative_to(workspace_memory)
    except AttributeError:
        # Python <3.9 compatibility fallback is irrelevant here, but keep the
        # path truth check conservative if the helper is reused elsewhere.
        return str(Path(gateway_db_path()).expanduser().resolve()).startswith(str(workspace_memory))
    except Exception:
        return False


def gateway_storage_diagnostics() -> dict[str, Any]:
    backend = gateway_store_backend()
    workspace_memory = _workspace_memory_path()
    dsn = gateway_postgres_dsn(required=False)
    return {
        "backend": backend,
        "canonical_store": backend if backend in {"sqlite", "postgres"} else "memory",
        "canonical_source": f"gateway-{backend}",
        "db_path": gateway_db_path(),
        "workspace_memory_path": str(workspace_memory) if workspace_memory else None,
        "db_path_is_workspace_memory": gateway_db_path_is_workspace_memory(),
        "postgres_dsn_configured": bool(dsn),
        "postgres_required": gateway_requires_postgres(),
    }


def validate_gateway_storage_config() -> None:
    backend = gateway_store_backend()
    if backend not in {"sqlite", "postgres", "memory"}:
        raise RuntimeError(f"Unsupported HG_GATEWAY_STORE backend: {backend}")
    if gateway_requires_postgres() and backend != "postgres":
        raise RuntimeError("HG_GATEWAY_REQUIRE_POSTGRES=1 requires HG_GATEWAY_STORE=postgres")
    if backend == "postgres":
        gateway_postgres_dsn(required=True)
