"""
Plugin SDK: manifest loading, install/enable/disable with audit events; capability checks.
PLUGIN_INSTALLED, PLUGIN_ENABLED, PLUGIN_DISABLED.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def load_plugin_manifest(manifest_path: Path) -> Dict[str, Any]:
    """
    Load and validate plugin manifest. Expects plugin_id, name, version, capabilities, signature.
    Returns manifest dict; raises ValueError if invalid.
    """
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("plugin_id", "name", "version", "capabilities", "signature"):
        if key not in data:
            raise ValueError(f"Manifest missing required field: {key}")
    if not isinstance(data["capabilities"], list):
        raise ValueError("capabilities must be a list")
    return data


def _registry_path(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "plugins" / "registry.json"


def _read_registry(workspace_root: Path) -> Dict[str, Any]:
    p = _registry_path(workspace_root)
    if not p.exists():
        return {"plugins": {}, "enabled": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"plugins": {}, "enabled": []}


def _write_registry(workspace_root: Path, data: Dict[str, Any]) -> None:
    p = _registry_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def register_plugin(
    *,
    manifest_path: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Register plugin from manifest: copy manifest into artifacts/plugins/manifests/, update registry, emit PLUGIN_INSTALLED.
    Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    manifest = load_plugin_manifest(manifest_path)
    plugin_id = manifest["plugin_id"]
    root = workspace_root / "artifacts" / "plugins" / "manifests"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{plugin_id}.json"
    dest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    reg = _read_registry(workspace_root)
    reg["plugins"][plugin_id] = {"path": str(dest), "version": manifest["version"], "capabilities": manifest.get("capabilities", [])}
    if plugin_id not in (reg.get("enabled") or []):
        reg.setdefault("enabled", [])
        if plugin_id not in reg["enabled"]:
            reg["enabled"].append(plugin_id)
    _write_registry(workspace_root, reg)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return emit(
        "PLUGIN_INSTALLED",
        "plugin",
        plugin_id,
        {"plugin_id": plugin_id, "version": manifest["version"], "manifest_path": str(dest), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def enable_plugin(
    *,
    plugin_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Add plugin to enabled list, emit PLUGIN_ENABLED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    reg = _read_registry(workspace_root)
    if plugin_id not in reg.get("plugins", {}):
        raise ValueError(f"Plugin not installed: {plugin_id}")
    enabled = reg.get("enabled") or []
    if plugin_id not in enabled:
        enabled.append(plugin_id)
        reg["enabled"] = enabled
        _write_registry(workspace_root, reg)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return emit(
        "PLUGIN_ENABLED",
        "plugin",
        plugin_id,
        {"plugin_id": plugin_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def disable_plugin(
    *,
    plugin_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Remove plugin from enabled list, emit PLUGIN_DISABLED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    reg = _read_registry(workspace_root)
    enabled = reg.get("enabled") or []
    if plugin_id in enabled:
        enabled.remove(plugin_id)
        reg["enabled"] = enabled
        _write_registry(workspace_root, reg)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return emit(
        "PLUGIN_DISABLED",
        "plugin",
        plugin_id,
        {"plugin_id": plugin_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def list_plugins(workspace_root: Path, enabled_only: bool = False) -> List[Dict[str, Any]]:
    """List registered plugins from registry; if enabled_only, filter to enabled list."""
    reg = _read_registry(Path(workspace_root))
    plugins = reg.get("plugins") or {}
    enabled = set(reg.get("enabled") or [])
    out = []
    for pid, info in plugins.items():
        if enabled_only and pid not in enabled:
            continue
        out.append({"plugin_id": pid, "version": info.get("version"), "capabilities": info.get("capabilities", []), "enabled": pid in enabled})
    return out


def check_plugin_capability(workspace_root: Path, plugin_id: str, capability: str) -> bool:
    """Return True if plugin is installed, enabled, and declares the capability."""
    reg = _read_registry(Path(workspace_root))
    if plugin_id not in (reg.get("enabled") or []):
        return False
    info = (reg.get("plugins") or {}).get(plugin_id)
    if not info:
        return False
    caps = info.get("capabilities") or []
    return capability in caps
