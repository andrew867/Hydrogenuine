"""Runtime store backend selection helpers."""

from __future__ import annotations

from hg_gateway.storage_config import gateway_requires_postgres, gateway_store_backend


def runtime_store_backend() -> str:
    return gateway_store_backend()


def runtime_requires_postgres() -> bool:
    return gateway_requires_postgres()
