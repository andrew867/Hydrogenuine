"""Pack 14: Data governance and privacy."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit

DATA_CLASSIFICATION_P0 = "P0"
DATA_CLASSIFICATION_P1 = "P1"
DATA_CLASSIFICATION_P2 = "P2"

DATA_POLICY_PUBLISHED = "DATA_POLICY_PUBLISHED"
ARTIFACT_CLASSIFIED = "ARTIFACT_CLASSIFIED"
EXPORT_REDACTION_APPLIED = "EXPORT_REDACTION_APPLIED"
EXPORT_DENIED_BY_DATA_POLICY = "EXPORT_DENIED_BY_DATA_POLICY"


def publish_data_policy(workspace_root: Path, policy: Dict[str, Any], scope: Dict[str, str], actor: Dict[str, str]) -> str:
    payload = {"policy": policy}
    return emit(DATA_POLICY_PUBLISHED, "artifact", policy.get("policy_id", "policy"), payload, scope=scope, actor=actor, workspace_root=workspace_root)


def check_export_allowed(classification: str, export_purpose: str, policy: Optional[Dict[str, Any]] = None):
    if classification == DATA_CLASSIFICATION_P0:
        allowed = (policy or {}).get("allowed_export_purposes", [])
        if export_purpose not in allowed and allowed != ["*"]:
            return False, "export_denied_p0_sensitive"
    return True, None


def apply_redaction_template(payload: Dict[str, Any], template: List[str]) -> Dict[str, Any]:
    out = dict(payload)
    for key in template:
        if key in out and key not in ("checksum", "sha256", "tombstone", "event_id"):
            del out[key]
    return out
