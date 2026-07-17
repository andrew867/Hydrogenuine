"""LM Studio endpoint networking for Docker containers.

Container must not assume 127.0.0.1 means host LM Studio.
Default: http://host.docker.internal:1234/v1
Supports: LAN IP, Tailscale IP, DNS name.
Endpoint reachability is NOT authorization.
Available model is NOT permission.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .runtime_config import RuntimeConfig

CONTAINER_LOCALHOST_WARNING = (
    "WARNING: 127.0.0.1 or localhost inside a Docker container refers to the "
    "container itself, NOT the host machine. Use host.docker.internal, a LAN IP, "
    "or a Tailscale IP to reach LM Studio running on the host."
)


@dataclass
class LmStudioEndpointCheck:
    base_url: str
    is_container_localhost: bool
    is_host_docker_internal: bool
    is_tailscale_ip: bool
    is_lan_ip: bool
    selected_model: str
    model_allowlisted: bool
    model_forbidden: bool
    forbidden_reason: str = ""
    endpoint_reachable: bool | None = None
    model_present: bool | None = None
    warning: str = ""


def _is_container_localhost(url: str) -> bool:
    return bool(re.search(r"(127\.0\.0\.1|localhost)(:\d+)?(/|$)", url))


def _is_host_docker_internal(url: str) -> bool:
    return "host.docker.internal" in url


def _is_tailscale_ip(url: str) -> bool:
    return bool(re.search(r"100\.\d+\.\d+\.\d+", url))


def _is_lan_ip(url: str) -> bool:
    return bool(re.search(r"(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)", url))


def check_model_allowed(model_id: str, cfg: RuntimeConfig) -> tuple[bool, bool, str]:
    model_lower = model_id.lower()
    for pattern in cfg.lmstudio_forbidden_patterns:
        if pattern.lower() in model_lower:
            return False, True, f"Model matches forbidden pattern: {pattern}"
    allowed = model_id in cfg.lmstudio_allowed_models
    return allowed, False, "" if allowed else f"Model not in allowed list"


def check_lmstudio_endpoint(cfg: RuntimeConfig) -> LmStudioEndpointCheck:
    url = cfg.lmstudio_base_url
    model = cfg.lmstudio_selected_model
    allowed, forbidden, reason = check_model_allowed(model, cfg)
    is_localhost = _is_container_localhost(url)

    return LmStudioEndpointCheck(
        base_url=url,
        is_container_localhost=is_localhost,
        is_host_docker_internal=_is_host_docker_internal(url),
        is_tailscale_ip=_is_tailscale_ip(url),
        is_lan_ip=_is_lan_ip(url),
        selected_model=model,
        model_allowlisted=allowed,
        model_forbidden=forbidden,
        forbidden_reason=reason,
        warning=CONTAINER_LOCALHOST_WARNING if is_localhost else "",
    )


def probe_lmstudio_health(base_url: str) -> tuple[bool, list[str]]:
    try:
        import urllib.request
        import json
        url = base_url.rstrip("/") + "/models" if not base_url.endswith("/models") else base_url
        if "/v1/models" not in url:
            url = base_url.rstrip("/").replace("/v1", "/v1/models")
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m.get("id", "") for m in data.get("data", [])]
            return True, models
    except Exception:
        return False, []
