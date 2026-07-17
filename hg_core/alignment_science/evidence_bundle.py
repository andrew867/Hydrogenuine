"""
Layer 9 Phase 5: Evidence bundle builder — build EvidenceBundle from artifact_refs; store and export for auditors.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from hg_core.alignment_science.schemas import (
    evidence_bundle,
    EvidenceBundle,
    validate_evidence_bundle,
)


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "evidence_bundles"


def build_evidence_bundle(
    workspace_root: Path,
    bundle_id: str,
    bundle_type: str,
    artifact_refs: List[str],
    summary: Optional[str] = None,
) -> EvidenceBundle:
    """Build and store an EvidenceBundle. bundle_type must be alignment_sufficient | alignment_failing | neutral."""
    workspace_root = Path(workspace_root)
    if bundle_type not in ("alignment_sufficient", "alignment_failing", "neutral"):
        raise ValueError(f"bundle_type must be alignment_sufficient | alignment_failing | neutral, got {bundle_type!r}")
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{bundle_id}.json"
    result = evidence_bundle(
        bundle_id=bundle_id,
        bundle_type=bundle_type,
        artifact_refs=artifact_refs,
        summary=summary,
    )
    result["artifact_ref"] = str(artifact_path)
    artifact_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def get_evidence_bundle(workspace_root: Path, bundle_id: str) -> Optional[EvidenceBundle]:
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{bundle_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("bundle_id") == bundle_id and validate_evidence_bundle(data):
                    return data
            except Exception:
                continue
    return None


def export_evidence_bundle(
    workspace_root: Path, bundle_id: str
) -> Optional[dict]:
    """
    Export bundle for auditors: returns dict with bundle_id, artifact_refs, summary, created_at, type.
    Returns None if bundle not found.
    """
    bundle = get_evidence_bundle(Path(workspace_root), bundle_id)
    if bundle is None:
        return None
    return {
        "bundle_id": bundle["bundle_id"],
        "type": bundle["type"],
        "artifact_refs": list(bundle["artifact_refs"]),
        "summary": bundle.get("summary"),
        "created_at": bundle.get("created_at"),
    }
