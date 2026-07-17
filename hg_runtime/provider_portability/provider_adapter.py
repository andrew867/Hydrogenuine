"""Provider adapter helpers."""

from __future__ import annotations

from hg_runtime.provider_portability.schemas import ProviderPortabilityError


def external_provider_call(*_args, **_kwargs) -> None:
    raise ProviderPortabilityError("external_provider_disabled_by_default")
