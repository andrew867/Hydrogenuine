"""Pre-long-soak model endpoint readiness checks.

Read-only. No mutation. Source is not truth. Model output is not truth.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class ModelCheckResult:
    name: str
    passed: bool
    detail: str = ""


def normalize_base_url(endpoint: str) -> str:
    url = endpoint.rstrip("/")
    url = re.sub(r"/v1/chat/completions$", "", url)
    url = re.sub(r"/v1/completions$", "", url)
    url = re.sub(r"/v1/models$", "", url)
    url = re.sub(r"/v1/embeddings$", "", url)
    url = re.sub(r"/v1$", "", url)
    return url


def models_url(endpoint: str) -> str:
    return normalize_base_url(endpoint) + "/v1/models"


def chat_completions_url(endpoint: str) -> str:
    return normalize_base_url(endpoint) + "/v1/chat/completions"


def check_endpoint_reachable(endpoint: str, timeout: int = 10) -> ModelCheckResult:
    try:
        import requests
        url = models_url(endpoint)
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return ModelCheckResult("endpoint_reachable", True, url)
        return ModelCheckResult("endpoint_reachable", False,
                                f"status {resp.status_code}")
    except Exception as e:
        return ModelCheckResult("endpoint_reachable", False, str(e)[:200])


def check_model_available(endpoint: str, model_name: str,
                          timeout: int = 10) -> ModelCheckResult:
    try:
        import requests
        url = models_url(endpoint)
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return ModelCheckResult("model_available", False,
                                    f"endpoint returned {resp.status_code}")
        data = resp.json()
        models = data.get("data", [])
        ids = [m.get("id", "") for m in models]
        if model_name in ids:
            return ModelCheckResult("model_available", True, model_name)
        return ModelCheckResult("model_available", False,
                                f"{model_name} not in {ids[:5]}")
    except Exception as e:
        return ModelCheckResult("model_available", False, str(e)[:200])


def discover_all_models(endpoint: str, timeout: int = 10) -> list[str]:
    try:
        import requests
        url = models_url(endpoint)
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
    except Exception:
        return []


def run_model_checks(endpoint: str, model_name: str,
                     timeout: int = 10) -> list[ModelCheckResult]:
    results = [check_endpoint_reachable(endpoint, timeout)]
    if results[0].passed:
        results.append(check_model_available(endpoint, model_name, timeout))
    else:
        results.append(ModelCheckResult("model_available", False,
                                         "skipped: endpoint unreachable"))
    return results


def compute_model_verdict(checks: list[ModelCheckResult],
                          model_required: bool = False) -> str:
    if all(c.passed for c in checks):
        return "GREEN"
    if model_required:
        return "RED"
    return "YELLOW_PROVIDER_UNAVAILABLE"
