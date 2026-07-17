"""
Event taxonomy registry: versioned list of ledger action enums and payload schema references.
Single source for validation and UI; artifact at artifacts/policy/event_taxonomy.yaml.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


def _default_taxonomy() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "actions": [
            {"action": "DECISION_COMMITTED", "payload_schema_ref": "decision", "severity": "state", "pii_handling": "none"},
            {"action": "OBSERVATION_RECORDED", "payload_schema_ref": "observation", "severity": "audit", "pii_handling": "configurable"},
            {"action": "MODULATION_APPLIED", "payload_schema_ref": "modulation", "severity": "state", "pii_handling": "none"},
            {"action": "REGULATORY_OVERRIDE_APPLIED", "payload_schema_ref": "override", "severity": "security", "pii_handling": "none"},
            {"action": "INCIDENT_CANDIDATE_CREATED", "payload_schema_ref": "incident_candidate", "severity": "audit", "pii_handling": "none"},
            {"action": "POLICY_PUBLISHED", "payload_schema_ref": "policy", "severity": "audit", "pii_handling": "none"},
            {"action": "AUDIT_BUNDLE_EXPORTED", "payload_schema_ref": "audit_export", "severity": "audit", "pii_handling": "none"},
        ],
    }


def load_event_taxonomy(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load event taxonomy from artifacts/policy/event_taxonomy.yaml; fallback to default."""
    root = Path(workspace_root or ".")
    path = root / "artifacts" / "policy" / "event_taxonomy.yaml"
    if not path.exists() or yaml is None:
        return _default_taxonomy()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else _default_taxonomy()
    except Exception:
        return _default_taxonomy()


def get_action_meta(taxonomy: Dict[str, Any], action: str) -> Optional[Dict[str, Any]]:
    """Return metadata for action (payload_schema_ref, severity, pii_handling, deprecated)."""
    actions = (taxonomy or {}).get("actions") or []
    for a in actions:
        if a.get("action") == action:
            return dict(a)
    return None


def list_actions(taxonomy: Dict[str, Any], include_deprecated: bool = True) -> List[str]:
    """Return list of action names; optionally exclude deprecated."""
    actions = (taxonomy or {}).get("actions") or []
    out = []
    for a in actions:
        if include_deprecated or not a.get("deprecated"):
            out.append(a.get("action", ""))
    return [x for x in out if x]
