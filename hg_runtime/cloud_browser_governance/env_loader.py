"""Load operator local env files without committing secrets."""

from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

ENV_CANDIDATES = (
    WORKSPACE / ".env.providers.local",
    WORKSPACE / ".env.providers",
    WORKSPACE / ".env.tools.local",
    WORKSPACE / ".env.tools",
)


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    value = value.strip().strip("'").strip('"')
    if not key:
        return None
    return key, value


def load_local_env_files(*, override: bool = False) -> list[str]:
    """Load provider/tool env files into os.environ. Returns loaded paths."""
    loaded: list[str] = []
    for path in ENV_CANDIDATES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parsed = _parse_env_line(line)
            if not parsed:
                continue
            key, value = parsed
            if override or key not in os.environ or not os.environ.get(key, "").strip():
                os.environ[key] = value
        loaded.append(str(path))
    return loaded


def live_browser_configured() -> bool:
    load_local_env_files()
    ext = os.environ.get("HG_EXTERNAL_NETWORK_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    allow = os.environ.get("HG_ALLOW_LIVE_BROWSER_TEST", "false").strip().lower() in {"1", "true", "yes"}
    return ext and allow


def live_cloud_configured() -> bool:
    load_local_env_files()
    cloud = os.environ.get("HG_CLOUD_PROVIDERS_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    allow = os.environ.get("HG_ALLOW_LIVE_CLOUD_TEST", "false").strip().lower() in {"1", "true", "yes"}
    return cloud and allow


__all__ = [
    "ENV_CANDIDATES",
    "live_browser_configured",
    "live_cloud_configured",
    "load_local_env_files",
    "parse_env_line",
]

# Back-compat alias for internal callers
parse_env_line = _parse_env_line
