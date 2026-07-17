"""CHRONO config loading (env + file) and untracked local-state persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.chrono.schema import Agent0TimeContext
from hg_runtime.chrono.sync import ChronoConfig

WORKSPACE = Path(__file__).resolve().parents[2]
LOCAL_STATE_DIR = WORKSPACE / ".hg-local" / "chrono"
LOCAL_STATE_FILE = LOCAL_STATE_DIR / "last_time_context.json"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def config_from_env(*, offline_fixture: bool = False) -> ChronoConfig:
    return ChronoConfig(
        ntp_host=os.environ.get("HG_NTP_HOST", "pool.ntp.org"),
        ntp_timeout_seconds=float(os.environ.get("HG_NTP_TIMEOUT_SECONDS", "3")),
        allow_network=_env_bool("HG_CHRONO_ALLOW_NETWORK", True),
        write_local_state=_env_bool("HG_CHRONO_WRITE_LOCAL_STATE", True),
        offline_fixture=offline_fixture,
    )


def load_config(path: str | Path) -> ChronoConfig:
    p = Path(path)
    if not p.is_file():
        p = WORKSPACE / path
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("permission_granted") or data.get("authority_created"):
        raise ValueError("chrono config must not grant permission or authority")
    return ChronoConfig(
        ntp_host=data.get("ntp_host", "pool.ntp.org"),
        ntp_timeout_seconds=float(data.get("ntp_timeout_seconds", 3)),
        allow_network=bool(data.get("allow_network", True)),
        write_local_state=bool(data.get("write_local_state", True)),
        offline_fixture=bool(data.get("offline_fixture", False)),
    )


def write_local_state(context: Agent0TimeContext) -> Path:
    """Persist last time context to an untracked local file."""
    LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_STATE_FILE.write_text(
        json.dumps(context.to_payload(), indent=2, sort_keys=True), encoding="utf-8"
    )
    return LOCAL_STATE_FILE


def read_local_state() -> dict[str, Any] | None:
    if not LOCAL_STATE_FILE.is_file():
        return None
    return json.loads(LOCAL_STATE_FILE.read_text(encoding="utf-8"))


__all__ = [
    "LOCAL_STATE_DIR",
    "LOCAL_STATE_FILE",
    "WORKSPACE",
    "config_from_env",
    "load_config",
    "read_local_state",
    "write_local_state",
]
