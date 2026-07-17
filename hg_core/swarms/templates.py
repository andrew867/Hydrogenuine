"""Pack 9: Template swarms - Ops Safe, Security Strict, Support Fast, Demo Mode."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

TEMPLATE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ops_safe": {
        "template_id": "ops_safe",
        "name": "Ops Safe",
        "description": "Conservative, strong verification, strict continuity",
        "roles": [{"role": "operator", "count": 1}, {"role": "agent", "count": 2}],
        "default_preset": "conservative",
        "default_trust_tier": "high",
        "verifier_diversity_required": True,
        "drift_threshold": 0.5,
        "safeguards_default": True,
        "connectors_enabled_by_default": False,
    },
    "security_strict": {
        "template_id": "security_strict",
        "name": "Security Strict",
        "description": "Maximum scrutiny, high quorum thresholds",
        "roles": [{"role": "operator", "count": 1}, {"role": "auditor", "count": 1}, {"role": "agent", "count": 1}],
        "default_preset": "low",
        "default_trust_tier": "maximum",
        "verifier_diversity_required": True,
        "drift_threshold": 0.4,
        "safeguards_default": True,
        "quorum_threshold_high_impact": 0.75,
        "connectors_enabled_by_default": False,
    },
    "support_fast": {
        "template_id": "support_fast",
        "name": "Support Fast",
        "description": "Quick, still verifiable, limited tool set",
        "roles": [{"role": "agent", "count": 3}],
        "default_preset": "normal",
        "default_trust_tier": "standard",
        "verifier_diversity_required": False,
        "drift_threshold": 0.7,
        "safeguards_default": True,
        "connectors_enabled_by_default": False,
    },
    "demo_mode": {
        "template_id": "demo_mode",
        "name": "Demo Mode",
        "description": "Safe redactions, seeded activity, guided tour enabled",
        "roles": [{"role": "agent", "count": 2}],
        "default_preset": "normal",
        "default_trust_tier": "standard",
        "verifier_diversity_required": False,
        "drift_threshold": 0.8,
        "safeguards_default": True,
        "connectors_enabled_by_default": False,
        "guided_tour_enabled": True,
        "seeded_activity": True,
    },
}


def _templates_artifact_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "swarm_templates"


def list_templates(workspace_root: Path) -> List[Dict[str, Any]]:
    """List templates: built-in plus any artifact overrides."""
    root = _templates_artifact_root(workspace_root)
    out = list(TEMPLATE_DEFAULTS.values())
    if root.exists():
        for path in sorted(root.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                tid = doc.get("template_id") or path.stem
                if tid in TEMPLATE_DEFAULTS:
                    out = [t for t in out if t.get("template_id") != tid]
                out.append(doc)
            except (json.JSONDecodeError, OSError):
                continue
    return out


def get_template_defaults(workspace_root: Path, template_id: str) -> Optional[Dict[str, Any]]:
    """Get template defaults by id."""
    root = _templates_artifact_root(workspace_root)
    path = root / f"{template_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return TEMPLATE_DEFAULTS.get(template_id)
