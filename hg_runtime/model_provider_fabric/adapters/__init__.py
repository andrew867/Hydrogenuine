"""External provider adapter contracts — disabled by default, dry-run only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.model_provider_fabric.config_loader import secret_available
from hg_runtime.model_provider_fabric.types import (
    ModelProviderConfig,
    ProviderReceipt,
    advisory_envelope,
)


@dataclass(frozen=True)
class ExternalProviderContract:
    provider_type: str
    requires_enable: bool = True
    requires_secret_env: str | None = None
    privacy_class: str = "external"
    live_calls_implemented: bool = False

    def validate_config(self, config: ModelProviderConfig) -> dict[str, Any]:
        failures: list[str] = []
        if self.requires_enable and not config.enabled:
            failures.append("provider disabled")
        if config.requires_secret and not secret_available(config):
            failures.append("DISABLED_MISSING_SECRET")
        if config.permission_granted or config.authority_created:
            failures.append("authority conversion forbidden")
        return advisory_envelope(
            schema="external-provider-contract-validation",
            provider_id=config.provider_id,
            provider_type=self.provider_type,
            ok=not failures,
            failures=failures,
            live_calls_implemented=self.live_calls_implemented,
            dry_run_only=True,
        )

    def dry_run_receipt(self, config: ModelProviderConfig, *, role: str, request_id: str) -> ProviderReceipt:
        return ProviderReceipt(
            receipt_id=f"mpf:contract:{config.provider_id}:{request_id}",
            provider_id=config.provider_id,
            model_id=config.model_id,
            role=role,  # type: ignore[arg-type]
            organ_id=None,
            request_id=request_id,
            outcome="dry_run_contract_ok",
            fallback_stub=False,
        )


OPENAI_COMPATIBLE = ExternalProviderContract(
    provider_type="openai_compatible",
    requires_secret_env="OPENAI_API_KEY",
    live_calls_implemented=False,
)
ANTHROPIC_COMPATIBLE = ExternalProviderContract(
    provider_type="anthropic_compatible",
    requires_secret_env="ANTHROPIC_API_KEY",
    live_calls_implemented=False,
)
XAI_COMPATIBLE = ExternalProviderContract(
    provider_type="xai_compatible",
    requires_secret_env="XAI_API_KEY",
    live_calls_implemented=False,
)
GENERIC_OPENAI_HTTP = ExternalProviderContract(
    provider_type="openai_compatible",
    requires_secret_env="HG_OPENAI_COMPAT_API_KEY",
    live_calls_implemented=False,
)

CONTRACTS = {
    "openai_compatible": OPENAI_COMPATIBLE,
    "anthropic_compatible": ANTHROPIC_COMPATIBLE,
    "xai_compatible": XAI_COMPATIBLE,
    "ollama": ExternalProviderContract(provider_type="ollama", requires_secret_env=None, live_calls_implemented=False),
    "vllm": ExternalProviderContract(provider_type="vllm", requires_secret_env=None, live_calls_implemented=False),
}


__all__ = [
    "ANTHROPIC_COMPATIBLE",
    "CONTRACTS",
    "ExternalProviderContract",
    "GENERIC_OPENAI_HTTP",
    "OPENAI_COMPATIBLE",
    "XAI_COMPATIBLE",
]

from hg_runtime.model_provider_fabric.adapters.cloud import (  # noqa: E402
    ADAPTERS,
    AnthropicProviderAdapter,
    OpenAIProviderAdapter,
    XAIProviderAdapter,
    get_adapter,
    live_cloud_allowed,
)

__all__ += ["ADAPTERS", "AnthropicProviderAdapter", "OpenAIProviderAdapter", "XAIProviderAdapter", "get_adapter", "live_cloud_allowed"]
