"""OpenVINO Windows provider health probe."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from hg_runtime.model_provider_fabric.types import ModelProviderConfig, OpenVINOVerdict, ProviderHealth

PROBE_URLS = (
    "http://host.docker.internal:18080/health",
    "http://127.0.0.1:18080/health",
)


def _http_json(url: str, timeout: float) -> tuple[bool, dict[str, Any] | str]:
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, str(exc)


def classify_openvino_verdict(payload: dict[str, Any]) -> OpenVINOVerdict:
    if payload.get("status") != "ok":
        return "YELLOW_PROVIDER_UNREACHABLE"
    if payload.get("fallback_stub_available") and not payload.get("model_loaded"):
        return "YELLOW_FALLBACK_STUB_ONLY"
    if payload.get("model_loaded") is True:
        return "GREEN_REAL_OPENVINO_WINDOWS"
    return "YELLOW_PROVIDER_CONTRACT_READY"


def probe_openvino_health(config: ModelProviderConfig) -> ProviderHealth:
    urls: list[str] = []
    if config.health_url:
        urls.append(config.health_url)
    if config.endpoint_url:
        base = config.endpoint_url.rstrip("/").removesuffix("/v1").removesuffix("/v3")
        urls.append(f"{base}/health")
    urls.extend(PROBE_URLS)
    override = os.environ.get("HG_OPENVINO_HEALTH_URL", "").strip()
    if override:
        urls.insert(0, override)

    seen: set[str] = set()
    last_error = ""
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        ok, payload = _http_json(url, timeout=float(config.timeout_seconds))
        if not ok:
            last_error = str(payload)
            continue
        if not isinstance(payload, dict):
            continue
        verdict = classify_openvino_verdict(payload)
        fallback_stub = bool(payload.get("fallback_stub_available")) and not bool(payload.get("model_loaded"))
        if payload.get("model_loaded") and not fallback_stub:
            fallback_stub = False
        return ProviderHealth(
            provider_id=config.provider_id,
            reachable=True,
            healthy=payload.get("status") == "ok",
            model_loaded=bool(payload.get("model_loaded")),
            resolved_device=payload.get("resolved_device"),
            fallback_stub=fallback_stub,
            openvino_verdict=verdict,
            detail=f"probed {url}",
        )

    return ProviderHealth(
        provider_id=config.provider_id,
        reachable=False,
        healthy=False,
        openvino_verdict="YELLOW_PROVIDER_UNREACHABLE",
        failure_reason="UNREACHABLE",
        detail=last_error or "no OpenVINO health endpoint reachable",
    )


__all__ = ["classify_openvino_verdict", "probe_openvino_health"]
