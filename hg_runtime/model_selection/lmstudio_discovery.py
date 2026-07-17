"""LM Studio model discovery via /v1/models.

No hard allowlist. No remote fallback. Model availability is not permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from hg_runtime.soak_readiness.model_doctor import models_url


@dataclass
class DiscoveryResult:
    endpoint: str
    models: list[str] = field(default_factory=list)
    reachable: bool = False
    error: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "endpoint_reachable": self.reachable,
            "models_discovered": len(self.models),
            "model_ids": self.models,
            "error": self.error,
            "timestamp": self.timestamp,
            "model_availability_is_not_permission": True,
            "no_hard_allowlist": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }


def discover_models(endpoint: str, timeout: int = 10) -> DiscoveryResult:
    result = DiscoveryResult(
        endpoint=endpoint,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    try:
        import requests
        url = models_url(endpoint)
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            result.error = f"status {resp.status_code}"
            return result
        data = resp.json()
        result.reachable = True
        result.models = [
            m.get("id", "") for m in data.get("data", []) if m.get("id")
        ]
    except Exception as e:
        result.error = str(e)[:200]
    return result
