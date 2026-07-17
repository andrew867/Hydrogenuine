"""Watchtower runtime configuration — local-only bind, explicit autostart."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = WORKSPACE / "configs/openvino_watchtower/watchtower_runtime.json"
LIFECYCLE_DIR = WORKSPACE / ".hg-local/openvino_watchtower/lifecycle"


@dataclass(frozen=True)
class WatchtowerRuntimeConfig:
    enabled: bool = False
    autostart: bool = False
    host: str = "127.0.0.1"
    port: int = 8791
    strict_start: bool = False
    stale_threshold_seconds: int = 120
    contact_lost_seconds: int = 300
    session_autostart: bool = False
    prometheus_enabled: bool = False
    ui_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "autostart": self.autostart,
            "host": self.host,
            "port": self.port,
            "strict_start": self.strict_start,
            "stale_threshold_seconds": self.stale_threshold_seconds,
            "contact_lost_seconds": self.contact_lost_seconds,
            "session_autostart": self.session_autostart,
            "prometheus_enabled": self.prometheus_enabled,
            "ui_enabled": self.ui_enabled,
        }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_runtime_config(path: Path | None = None) -> WatchtowerRuntimeConfig:
    cfg_path = path or DEFAULT_CONFIG
    data: dict[str, Any] = {}
    if cfg_path.is_file():
        data = json.loads(cfg_path.read_text(encoding="utf-8"))

    enabled = _env_bool("HG_OPENVINO_WATCHTOWER_ENABLED", bool(data.get("enabled", False)))
    autostart = _env_bool("HG_OPENVINO_WATCHTOWER_AUTOSTART", bool(data.get("autostart", False)))
    host = os.environ.get("HG_OPENVINO_WATCHTOWER_HOST", str(data.get("host", "127.0.0.1")))
    port = _env_int("HG_OPENVINO_WATCHTOWER_PORT", int(data.get("port", 8791)))
    strict_start = _env_bool("HG_OPENVINO_WATCHTOWER_STRICT_START", bool(data.get("strict_start", False)))

    return WatchtowerRuntimeConfig(
        enabled=enabled,
        autostart=autostart,
        host=host,
        port=port,
        strict_start=strict_start,
        stale_threshold_seconds=int(data.get("stale_threshold_seconds", 120)),
        contact_lost_seconds=int(data.get("contact_lost_seconds", 300)),
        session_autostart=bool(data.get("session_autostart", False)),
        prometheus_enabled=bool(data.get("prometheus_enabled", False)),
        ui_enabled=bool(data.get("ui_enabled", True)),
    )


def validate_host(host: str) -> tuple[bool, str | None]:
    normalized = (host or "").strip().lower()
    if normalized in {"127.0.0.1", "localhost", "::1"}:
        return True, None
    return False, f"external bind denied: {host}"


__all__ = ["LIFECYCLE_DIR", "WatchtowerRuntimeConfig", "load_runtime_config", "validate_host"]
