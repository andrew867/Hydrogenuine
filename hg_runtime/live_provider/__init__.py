"""Live provider dry autonomy — Phase 15 integration layer."""

from hg_runtime.live_provider.schema import (
    LiveProviderVerdict,
    ModelIdentity,
    ProviderHealthReceipt,
    ProviderIdentity,
    ProviderOutputReceipt,
)

__all__ = [
    "LiveProviderVerdict",
    "ModelIdentity",
    "ProviderHealthReceipt",
    "ProviderIdentity",
    "ProviderOutputReceipt",
    "probe_provider_health",
    "complete_json",
    "run_dry_provider_turn",
]


def probe_provider_health(*args, **kwargs):
    from hg_runtime.live_provider.provider_health import probe_provider_health as _probe

    return _probe(*args, **kwargs)


def complete_json(*args, **kwargs):
    from hg_runtime.live_provider.provider_router import complete_json as _complete

    return _complete(*args, **kwargs)


def run_dry_provider_turn(*args, **kwargs):
    from hg_runtime.live_provider.provider_router import run_dry_provider_turn as _run

    return _run(*args, **kwargs)
