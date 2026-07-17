from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

LIVE_SOCIAL_ENABLE_ENV = "HG_ENABLE_LIVE_SOCIAL_APIS"


def _resolve_runtime_env_var(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    try:
        cfg = Path.home() / ".hg" / "hg.json"
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            env_vars = ((data.get("env") or {}).get("vars") or {})
            if isinstance(env_vars, dict):
                raw = env_vars.get(name)
                if raw is not None:
                    return str(raw).strip()
    except Exception:
        pass
    return ""


def live_social_enabled() -> bool:
    raw = _resolve_runtime_env_var(LIVE_SOCIAL_ENABLE_ENV).lower()
    return raw in {"1", "true", "yes", "on"}


def text_only_mode() -> bool:
    return not live_social_enabled()


def read_flag_value(flag: str, argv: list[str]) -> Optional[str]:
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
    return None

