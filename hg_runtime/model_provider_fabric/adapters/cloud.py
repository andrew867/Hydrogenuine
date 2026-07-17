"""Cloud provider adapters — OpenAI, Anthropic, xAI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from hg_runtime.cloud_browser_governance.secrets import load_secret_refs
from hg_runtime.cloud_browser_governance.types import FIXTURE_CLOCK, advisory_envelope, redact_secrets, stable_hash
from hg_runtime.model_provider_fabric.config_loader import secret_available
from hg_runtime.model_provider_fabric.types import ModelProviderConfig, ProviderReceipt


def cloud_providers_enabled() -> bool:
    return os.environ.get("HG_CLOUD_PROVIDERS_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def live_cloud_allowed() -> bool:
    return cloud_providers_enabled() and os.environ.get("HG_ALLOW_LIVE_CLOUD_TEST", "false").strip().lower() in {"1", "true", "yes"}


@dataclass
class CloudAdapterBase:
    provider_type: str
    secret_env: str
    default_endpoint: str

    def validate_config(self, config: ModelProviderConfig) -> dict[str, Any]:
        secret_present = secret_available(config)
        failures: list[str] = []
        if config.permission_granted or config.authority_created:
            failures.append("authority_forbidden")
        if config.enabled and not cloud_providers_enabled():
            failures.append("HG_CLOUD_PROVIDERS_ENABLED=false")
        if config.requires_secret and not secret_present:
            failures.append("DISABLED_MISSING_SECRET")
        return advisory_envelope(
            schema="cloud-adapter-validation",
            provider_id=config.provider_id,
            provider_type=self.provider_type,
            ok=not failures,
            failures=failures,
            secret_present=secret_present,
            secret_value_included=False,
            enabled=config.enabled,
            live_allowed=live_cloud_allowed(),
        )

    def dry_run_health(self, config: ModelProviderConfig) -> dict[str, Any]:
        v = self.validate_config(config)
        return advisory_envelope(
            schema="cloud-adapter-health",
            provider_id=config.provider_id,
            healthy=v["ok"] and config.enabled,
            reachable=False,
            dry_run_only=not live_cloud_allowed(),
            validation=v,
        )

    def _http_post(self, url: str, headers: dict[str, str], body: dict[str, Any], timeout: float) -> tuple[bool, Any]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return False, redact_secrets(str(exc))

    def inference(
        self,
        config: ModelProviderConfig,
        *,
        prompt: str,
        request_id: str,
        role: str = "ORGAN_HEAVY_REASONING",
        max_tokens: int = 32,
    ) -> dict[str, Any]:
        validation = self.validate_config(config)
        if not validation["ok"]:
            return advisory_envelope(schema="cloud-inference-denied", validation=validation, executed=False)
        from hg_runtime.cloud_browser_governance.budget import ProviderBudgetGovernor

        governor = ProviderBudgetGovernor()
        budget = governor.check_budget(tokens=max_tokens, cost_usd=0.001, cost_unknown=config.cost_class == "unknown")
        if not budget.get("allowed"):
            governor.release_request()
            return advisory_envelope(schema="cloud-inference-denied", budget=budget, executed=False)
        if not live_cloud_allowed():
            receipt = ProviderReceipt(
                receipt_id=f"cloud:dry:{config.provider_id}:{request_id}",
                provider_id=config.provider_id,
                model_id=config.model_id,
                role=role,  # type: ignore[arg-type]
                organ_id=None,
                request_id=request_id,
                outcome="dry_run_contract_ok",
                tokens_approx=len(prompt.split()),
            )
            governor.release_request()
            return advisory_envelope(
                schema="cloud-inference-dry-run",
                receipt=receipt.to_payload(),
                executed=False,
                response_preview="[dry-run only; enable HG_ALLOW_LIVE_CLOUD_TEST for tiny live probe]",
            )
        # Tiny live probe only when explicitly allowed
        result = self._live_call(config, prompt=prompt, max_tokens=max_tokens)
        governor.release_request()
        payload = advisory_envelope(
            schema="cloud-inference-result",
            provider_id=config.provider_id,
            executed=result.get("ok", False),
            result=result,
            timestamp=FIXTURE_CLOCK,
        )
        payload["receipt_hash"] = stable_hash(payload)
        return payload

    def _live_call(self, config: ModelProviderConfig, *, prompt: str, max_tokens: int) -> dict[str, Any]:
        # Fail closed: the base adapter refuses live calls outright; live cloud
        # probes are a per-adapter opt-in behind HG_ALLOW_LIVE_CLOUD_TEST.
        raise RuntimeError(
            f"{self.provider_type} base adapter refuses live calls; "
            "concrete adapters implement _live_call explicitly"
        )


class OpenAIProviderAdapter(CloudAdapterBase):
    def __init__(self) -> None:
        super().__init__(provider_type="openai_compatible", secret_env="OPENAI_API_KEY", default_endpoint="https://api.openai.com/v1")

    def _live_call(self, config: ModelProviderConfig, *, prompt: str, max_tokens: int) -> dict[str, Any]:
        key = os.environ.get(config.secret_env_var or "OPENAI_API_KEY", "")
        url = f"{(config.endpoint_url or self.default_endpoint).rstrip('/')}/chat/completions"
        body = {"model": config.model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
        ok, resp = self._http_post(url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body, float(config.timeout_seconds))
        return {"ok": ok, "response": resp if ok else resp}


class AnthropicProviderAdapter(CloudAdapterBase):
    def __init__(self) -> None:
        super().__init__(provider_type="anthropic_compatible", secret_env="ANTHROPIC_API_KEY", default_endpoint="https://api.anthropic.com/v1")

    def _live_call(self, config: ModelProviderConfig, *, prompt: str, max_tokens: int) -> dict[str, Any]:
        key = os.environ.get(config.secret_env_var or "ANTHROPIC_API_KEY", "")
        url = f"{(config.endpoint_url or self.default_endpoint).rstrip('/')}/messages"
        body = {"model": config.model_id, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        ok, resp = self._http_post(
            url,
            {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            body,
            float(config.timeout_seconds),
        )
        return {"ok": ok, "response": resp if ok else resp}


class XAIProviderAdapter(CloudAdapterBase):
    def __init__(self) -> None:
        super().__init__(provider_type="xai_compatible", secret_env="XAI_API_KEY", default_endpoint="https://api.x.ai/v1")

    def _live_call(self, config: ModelProviderConfig, *, prompt: str, max_tokens: int) -> dict[str, Any]:
        key = os.environ.get(config.secret_env_var or "XAI_API_KEY", "")
        url = f"{(config.endpoint_url or self.default_endpoint).rstrip('/')}/chat/completions"
        body = {"model": config.model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
        ok, resp = self._http_post(url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body, float(config.timeout_seconds))
        return {"ok": ok, "response": resp if ok else resp}


ADAPTERS = {
    "openai_compatible": OpenAIProviderAdapter(),
    "openai_responses": OpenAIProviderAdapter(),
    "openai_chat_completions": OpenAIProviderAdapter(),
    "anthropic_compatible": AnthropicProviderAdapter(),
    "anthropic_messages": AnthropicProviderAdapter(),
    "xai_compatible": XAIProviderAdapter(),
    "xai_chat_completions": XAIProviderAdapter(),
}


def get_adapter(provider_type: str) -> CloudAdapterBase | None:
    return ADAPTERS.get(provider_type)


__all__ = ["ADAPTERS", "AnthropicProviderAdapter", "OpenAIProviderAdapter", "XAIProviderAdapter", "get_adapter", "live_cloud_allowed"]
