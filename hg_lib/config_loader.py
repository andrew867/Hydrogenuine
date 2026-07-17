"""
Central Hydrogenuine config loader.
Loads memory/hg_config.yaml (or hg_config.yaml), applies HG_* env overrides, optional validation.
See docs/specs/central_config_spec.md.
"""

from pathlib import Path
import os

from hg_lib.errors import HydrogenuineError

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

CONFIG_FILENAMES = ["memory/hg_config.yaml", "memory/hg_config.yml", "hg_config.yaml", "hg_config.yml"]
ENV_PREFIX = "HG_"
DEFAULT_SECTIONS = ("memory", "overseer", "platform")
# Normalize env section name to config section (OVERSER -> overseer)
ENV_SECTION_TO_CONFIG = {"memory": "memory", "overser": "overseer", "overseer": "overseer", "platform": "platform"}

# Keys that should be coerced to bool (env value "true"/"false" -> True/False)
BOOL_KEYS = frozenset({
    "dry_run", "dry_run_mode", "enabled", "strict", "validate",
})


def _coerce_value(key: str, raw: str):  # type: ignore
    """Coerce env string to bool or number when appropriate."""
    lower = raw.strip().lower()
    if key.lower() in BOOL_KEYS or lower in ("true", "false"):
        return lower == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _apply_env_overrides(config: dict, workspace_root: Path | None) -> None:
    """Mutate config by applying HG_<SECTION>_<KEY> env vars."""
    for env_key, value in os.environ.items():
        if not env_key.startswith(ENV_PREFIX) or env_key == ENV_PREFIX.rstrip("_"):
            continue
        rest = env_key[len(ENV_PREFIX):]
        parts = rest.split("_", 1)
        if len(parts) != 2:
            continue
        section_raw = parts[0].lower()
        section = ENV_SECTION_TO_CONFIG.get(section_raw, section_raw)
        key = parts[1].lower()
        if section not in config:
            config[section] = {}
        config[section][key] = _coerce_value(key, value)


def _validate_config(config: dict, strict: bool, raw_loaded: dict | None = None) -> None:
    """Optional validation: ensure sections are dicts; if strict, require allowed keys only in raw_loaded."""
    # Validate raw file content: any defined section must be a dict
    if raw_loaded:
        for section in DEFAULT_SECTIONS:
            if section in raw_loaded and not isinstance(raw_loaded[section], dict):
                raise HydrogenuineError(
                    f"Config section '{section}' must be a dict.",
                    code="CONFIG_INVALID",
                )
    for section in DEFAULT_SECTIONS:
        if section in config and not isinstance(config.get(section), dict):
            raise HydrogenuineError(
                f"Config section '{section}' must be a dict.",
                code="CONFIG_INVALID",
            )
    if strict and raw_loaded:
        allowed = set(DEFAULT_SECTIONS)
        for key in raw_loaded:
            if key not in allowed:
                raise HydrogenuineError(
                    f"Unknown config section '{key}'. Allowed: {list(allowed)}",
                    code="CONFIG_INVALID",
                )


def load_config(
    workspace_root: Path | None = None,
    *,
    validate: bool = True,
    strict: bool = False,
) -> dict:
    """
    Load central config from memory/hg_config.yaml or hg_config.yaml under workspace_root.
    Applies HG_<SECTION>_<KEY> env overrides. Returns dict with keys memory, overseer, platform
    (missing file or section -> empty dict for that section).
    """
    if workspace_root is None:
        from hg_lib.config import get_workspace_root
        workspace_root = get_workspace_root()

    config = {s: {} for s in DEFAULT_SECTIONS}

    if yaml is None:
        _apply_env_overrides(config, workspace_root)
        if validate:
            _validate_config(config, strict)
        return config

    loaded = None
    for rel in CONFIG_FILENAMES:
        path = workspace_root / rel
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
            except Exception as e:
                raise HydrogenuineError(
                    f"Failed to load config from {path}: {e}",
                    code="CONFIG_LOAD_ERROR",
                )
            break

    if isinstance(loaded, dict):
        for section in DEFAULT_SECTIONS:
            if section in loaded and isinstance(loaded[section], dict):
                config[section] = dict(loaded[section])

    _apply_env_overrides(config, workspace_root)
    if validate:
        _validate_config(config, strict, raw_loaded=loaded if isinstance(loaded, dict) else None)
    return config


_cached_config: dict | None = None


def get_config(workspace_root: Path | None = None, *, reload: bool = False) -> dict:
    """Return cached config; load and cache if not yet loaded. Set reload=True to force reload."""
    global _cached_config
    if reload or _cached_config is None:
        _cached_config = load_config(workspace_root=workspace_root)
    return _cached_config
