"""
Pack 6: Secrets provider interface and implementations.
- EnvSecretsProvider: load from environment (required baseline).
- VaultSecretsProvider: optional; stub with clear interface for future Vault integration.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class SecretsProvider(ABC):
    """Interface for resolving secrets by key. No secrets in repo or client UI."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Return secret value for key, or None if not set."""
        ...


class EnvSecretsProvider(SecretsProvider):
    """Load secrets from environment variables. Key is mapped to env name (e.g. HG_GATEWAY_API_KEY)."""

    def __init__(self, prefix: str = "HG_", key_to_env: Optional[dict[str, str]] = None):
        self._prefix = prefix
        self._key_to_env = key_to_env or {}

    def get(self, key: str) -> Optional[str]:
        env_name = self._key_to_env.get(key) or (self._prefix + key.upper().replace(".", "_"))
        value = os.environ.get(env_name, "").strip()
        return value or None


class VaultSecretsProvider(SecretsProvider):
    """
    Optional Vault/KMS integration. Not implemented; interface for roadmap.
    Future: read from Vault path or cloud secret manager; same get(key) contract.
    """

    def __init__(self, vault_addr: str = "", mount: str = "secret", path_prefix: str = "hg/"):
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "")
        self._mount = mount
        self._path_prefix = path_prefix

    def get(self, key: str) -> Optional[str]:
        # Stub: not implemented; production Vault integration is on the roadmap.
        return None


def get_default_provider() -> SecretsProvider:
    """Return EnvSecretsProvider as the default (env vars as baseline)."""
    return EnvSecretsProvider()
