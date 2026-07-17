"""CT-02 SEC-U1 resolver tests."""

from __future__ import annotations

import pytest

from hg_core.secrets.resolver import SecretRefusal, SecretResolver
from hg_core.security.secrets_provider import SecretsProvider


class _FakeProvider(SecretsProvider):
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get(self, key: str) -> str | None:
        return self._values.get(key)


def test_sec_u1_resolve_in_call_scope_only() -> None:
    resolver = SecretResolver(_FakeProvider({"local-operator-key": "gate-secret-value"}))
    with pytest.raises(SecretRefusal, match="resolver_outside_call_scope"):
        resolver.resolve("secret_ref:local-operator-key")
    with resolver.call_scope():
        value = resolver.resolve("secret_ref:local-operator-key")
        assert value == "gate-secret-value"
    with pytest.raises(SecretRefusal, match="resolver_outside_call_scope"):
        resolver.resolve("secret_ref:local-operator-key")


def test_sec_u8_invalid_secret_ref_refused() -> None:
    resolver = SecretResolver(_FakeProvider({"k": "v"}))
    with resolver.call_scope():
        with pytest.raises(SecretRefusal, match="invalid_secret_ref_format"):
            resolver.resolve("raw-api-key-value")
