"""Pack 14: Supply chain integrity."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger import emit

PLUGIN_REVOKED = "PLUGIN_REVOKED"
CONNECTOR_CERT_REVOKED = "CONNECTOR_CERT_REVOKED"


def revoke_plugin(plugin_id: str, workspace_root: Path, scope: Dict[str, str], actor: Dict[str, str], reason: str = "") -> str:
    return emit(PLUGIN_REVOKED, "plugin", plugin_id, {"reason": reason, "quarantine": True}, scope=scope, actor=actor, workspace_root=workspace_root)


def get_sbom_refs(workspace_root: Path) -> List[Dict[str, Any]]:
    root = Path(workspace_root)
    out = []
    sbom_dir = root / "artifacts" / "sbom"
    if sbom_dir.exists():
        for f in sbom_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                out.append({"path": str(f), "digest": data.get("digest", ""), "name": f.stem})
            except Exception:
                pass
    return out
