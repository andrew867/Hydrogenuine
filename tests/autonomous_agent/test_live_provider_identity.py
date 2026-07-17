"""Provider identity tests."""
from __future__ import annotations

from hg_runtime.live_provider.provider_identity import (
    build_model_identity,
    build_provider_identity,
    provider_configured,
    unavailable_verdict_for_kind,
)
from hg_runtime.live_provider.schema import LiveProviderKind, LiveProviderVerdict


def test_dry_unavailable_not_configured(monkeypatch):
    monkeypatch.setenv("HG_LIVE_PROVIDER_KIND", "dry_unavailable")
    provider = build_provider_identity(provider_kind=LiveProviderKind.DRY_UNAVAILABLE)
    assert not provider_configured(provider)
    assert unavailable_verdict_for_kind(LiveProviderKind.DRY_UNAVAILABLE) == LiveProviderVerdict.YELLOW_LOCAL_MODEL_NOT_CONFIGURED


def test_model_identity_has_provider_ref():
    provider = build_provider_identity(provider_kind=LiveProviderKind.DRY_UNAVAILABLE)
    model = build_model_identity(provider)
    assert model.provider_ref == provider.provider_id
    assert model.hash
