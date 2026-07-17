"""Call-scoped secret resolver — sole resolution path for secret_ref handles (CT-02)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from hg_core.security.secrets_provider import SecretsProvider, get_default_provider


class SecretRefusal(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SecretResolver:
    """Resolves secret_ref handles in a call scope; values must not be persisted."""

    def __init__(self, provider: SecretsProvider | None = None) -> None:
        self._provider = provider or get_default_provider()
        self._scope_depth = 0

    @property
    def in_call_scope(self) -> bool:
        return self._scope_depth > 0

    def resolve(self, secret_ref: str) -> str:
        if not self.in_call_scope:
            raise SecretRefusal("resolver_outside_call_scope")
        if not secret_ref.startswith("secret_ref:"):
            raise SecretRefusal("invalid_secret_ref_format")
        key = secret_ref[len("secret_ref:") :]
        if not key or key.strip() != key:
            raise SecretRefusal("invalid_secret_ref_key")
        value = self._provider.get(key)
        if not value:
            raise SecretRefusal("secret_unresolved")
        return value

    @contextmanager
    def call_scope(self) -> Iterator["SecretResolver"]:
        self._scope_depth += 1
        try:
            yield self
        finally:
            self._scope_depth -= 1


_DEFAULT_RESOLVER: Optional[SecretResolver] = None


def default_resolver() -> SecretResolver:
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        _DEFAULT_RESOLVER = SecretResolver()
    return _DEFAULT_RESOLVER


__all__ = ["SecretRefusal", "SecretResolver", "default_resolver"]
