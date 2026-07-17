"""Ch4 Demo mode: toggles (demo_mode, live_actions_enabled, allow_fault_injection, sample_dataset_profile)."""

import json
import os
from pathlib import Path
from typing import Any


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _config_path() -> Path | None:
    root = _workspace_root()
    if not root:
        return None
    return root / "memory" / "overseer" / "demo_config.json"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def get_demo_config() -> dict[str, Any]:
    """Load demo config. Defaults: demo_mode True, live_actions_enabled False (investor-safe)."""
    defaults = {
        "demo_mode": _env_flag("HG_DEMO_MODE", default=True),
        "live_actions_enabled": _env_flag("HG_DEMO_LIVE_ACTIONS_ENABLED", default=False),
        "allow_fault_injection": _env_flag("HG_DEMO_ALLOW_FAULT_INJECTION", default=False),
        "sample_dataset_profile": (os.getenv("HG_DEMO_DATASET_PROFILE") or "medium").strip() or "medium",
    }
    path = _config_path()
    if not path or not path.exists():
        return defaults
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        defaults.update(data)
        return defaults
    except (json.JSONDecodeError, OSError):
        return defaults


def save_demo_config(config: dict[str, Any]) -> bool:
    """Persist demo config (admin only)."""
    path = _config_path()
    if not path:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except OSError:
        return False
