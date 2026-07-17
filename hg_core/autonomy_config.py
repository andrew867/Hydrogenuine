"""
Autonomy config: outbound safety gate and entity DAG change control.

Reads from memory/overseer/autonomy_config.json. Env overrides:
- HG_ENTITY_DAG_CHANGE_CONTROL: off | on | pass-through (default pass-through)
- HG_OUTBOUND_SAFETY_GATE_ENABLED: 1|0 or true|false (default false/OFF)

See token_optimization_and_autonomy_plumbing plan §5 and §4 (safety rails).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

AUTONOMY_CONFIG_PATH = "memory/overseer/autonomy_config.json"
ENTITY_DAG_CHANGE_CONTROL_VALUES = ("off", "on", "pass-through")
DEFAULT_ENTITY_DAG_CHANGE_CONTROL = "pass-through"
DEFAULT_OUTBOUND_SAFETY_GATE_ENABLED = False


def _load_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    try:
        from hg_lib.config import get_workspace_root
        root = workspace_root or get_workspace_root()
    except Exception:
        return {}
    path = root / AUTONOMY_CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load autonomy config %s: %s", path, e)
        return {}


def get_entity_dag_change_control(workspace_root: Optional[Path] = None) -> str:
    """
    Return entity DAG change control mode: off | on | pass-through.
    Default: pass-through (auto-approve valid proposals with same monitoring as on).
    Env override: HG_ENTITY_DAG_CHANGE_CONTROL.
    """
    raw = os.environ.get("HG_ENTITY_DAG_CHANGE_CONTROL", "").strip().lower()
    if raw in ENTITY_DAG_CHANGE_CONTROL_VALUES:
        return raw
    config = _load_config(workspace_root)
    mode = config.get("entity_dag_change_control")
    if isinstance(mode, str) and mode.lower() in ENTITY_DAG_CHANGE_CONTROL_VALUES:
        return mode.lower()
    return DEFAULT_ENTITY_DAG_CHANGE_CONTROL


def get_outbound_safety_gate_enabled(workspace_root: Optional[Path] = None) -> bool:
    """
    Return whether the outbound safety gate is enabled (blocks disallowed content when on).
    Default: False (OFF). Env override: HG_OUTBOUND_SAFETY_GATE_ENABLED.
    """
    raw = os.environ.get("HG_OUTBOUND_SAFETY_GATE_ENABLED", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    config = _load_config(workspace_root)
    val = config.get("outbound_safety_gate_enabled")
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("1", "true", "yes")
    return DEFAULT_OUTBOUND_SAFETY_GATE_ENABLED


def get_autonomy_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return full autonomy config dict (for API GET). Env overrides applied."""
    config = _load_config(workspace_root)
    return {
        "entity_dag_change_control": get_entity_dag_change_control(workspace_root),
        "outbound_safety_gate_enabled": get_outbound_safety_gate_enabled(workspace_root),
        **{k: v for k, v in config.items() if k not in ("entity_dag_change_control", "outbound_safety_gate_enabled")},
    }


def save_autonomy_config(
    entity_dag_change_control: Optional[str] = None,
    outbound_safety_gate_enabled: Optional[bool] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist autonomy config to memory/overseer/autonomy_config.json. Returns updated config."""
    try:
        from hg_lib.config import get_workspace_root
        root = workspace_root or get_workspace_root()
    except Exception:
        return get_autonomy_config(workspace_root)
    path = root / AUTONOMY_CONFIG_PATH
    config = _load_config(root)
    if entity_dag_change_control is not None and entity_dag_change_control.lower() in ENTITY_DAG_CHANGE_CONTROL_VALUES:
        config["entity_dag_change_control"] = entity_dag_change_control.lower()
    if outbound_safety_gate_enabled is not None:
        config["outbound_safety_gate_enabled"] = bool(outbound_safety_gate_enabled)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        logger.warning("Could not save autonomy config %s: %s", path, e)
    return get_autonomy_config(root)
