"""
Control Surface Pack 11: Branding config — placeholder-only until legal clearance.
Returns PROJECT_NAME_PLACEHOLDER and version for UI/API/docs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

# Default branding (Hydrogenuine); overridable via name_map file
DEFAULT_BRANDING: Dict[str, str] = {
    "project_name": "Hydrogenuine",
    "project_short": "Hg",
    "project_domain": "hydrogenuine.io",
    "version": "0.3.0",
}


def get_branding(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Return UI branding placeholders and version. Uses name_map if present at
    artifacts/branding/name_map.json or NAMING/name_map.json; otherwise defaults.
    """
    out: Dict[str, Any] = dict(DEFAULT_BRANDING)
    root = Path(workspace_root or ".")
    for path in [
        root / "artifacts" / "branding" / "name_map.json",
        root / "NAMING" / "name_map.json",
        root / ".cursor" / "plans" / "controlsurface" / "control_surface_pack11_integration_naming_project_rename" / "NAMING" / "name_map.example.json",
    ]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("PROJECT_NAME_PLACEHOLDER"):
                    out["project_name"] = data["PROJECT_NAME_PLACEHOLDER"]
                if data.get("PROJECT_SHORT_PLACEHOLDER"):
                    out["project_short"] = data["PROJECT_SHORT_PLACEHOLDER"]
                if data.get("PROJECT_DOMAIN_PLACEHOLDER"):
                    out["project_domain"] = data["PROJECT_DOMAIN_PLACEHOLDER"]
            except (json.JSONDecodeError, OSError):
                pass
            break
    return out


# Disallowed brand strings for CI. Use Hydrogenuine or hg only in code and docs.
DISALLOWED_BRAND_STRINGS: list[str] = [
    "YOUR_NEW_NAME_HERE",
    "YOUR_SHORT_NAME",
    "openclaw",
    "OpenClaw",
    "OPENCLAW",
]
