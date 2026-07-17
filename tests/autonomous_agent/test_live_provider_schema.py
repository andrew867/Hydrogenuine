"""Live provider schema tests."""
from __future__ import annotations

import pytest

from hg_runtime.live_provider.errors import LiveProviderConfigError
from hg_runtime.live_provider.schema import (
    LiveProviderKind,
    LiveProviderVerdict,
    ModelIdentity,
    ProviderIdentity,
    ProviderRuntimeMode,
    load_live_provider_policy,
    validate_policy_constraints,
)


def test_policy_rejects_fallback_as_cognition(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.live_provider.schema.load_live_provider_policy",
        lambda **_: {"fallback_as_cognition_allowed": True},
    )
    with pytest.raises(LiveProviderConfigError):
        validate_policy_constraints()


def test_provider_identity_hash_deterministic():
    p = ProviderIdentity(
        provider_id="p1",
        provider_kind=LiveProviderKind.DRY_UNAVAILABLE,
        provider_name="Dry",
        transport="none",
        runtime_mode=ProviderRuntimeMode.DRY_AUTONOMY,
        configured_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    p2 = ProviderIdentity(
        provider_id="p1",
        provider_kind=LiveProviderKind.DRY_UNAVAILABLE,
        provider_name="Dry",
        transport="none",
        runtime_mode=ProviderRuntimeMode.DRY_AUTONOMY,
        configured_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    assert p.hash == p2.hash


def test_model_identity_hash_deterministic():
    m = ModelIdentity(model_id="m1", provider_ref="p1").with_hash()
    m2 = ModelIdentity(model_id="m1", provider_ref="p1").with_hash()
    assert m.hash == m2.hash


def test_policy_file_exists():
    pol = load_live_provider_policy()
    assert pol.get("live_writes_allowed") is False
    assert pol.get("provider_receipt_required") is True
