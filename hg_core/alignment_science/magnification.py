"""
Layer 9 Phase 4: Human-in-the-loop magnification hooks — stub: human_feedback_artifact_ref -> magnified artifact.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.alignment_science.schemas import magnification_result, MagnificationResult, validate_magnification_result


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "magnification"


def run_magnification(
    workspace_root: Path,
    human_feedback_artifact_ref: str,
    magnification_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> MagnificationResult:
    """
    Stub: write a magnified feedback artifact that references the input; store MagnificationResult; optionally emit MAGNIFICATION_COMPLETED.
    """
    workspace_root = Path(workspace_root)
    mag_id = magnification_id or str(uuid.uuid4())
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    magnified_path = root / f"{mag_id}_magnified.json"
    magnified_content = {
        "source_ref": human_feedback_artifact_ref,
        "magnified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "stub",
        "count": 1,
    }
    magnified_path.write_text(json.dumps(magnified_content, indent=2, ensure_ascii=False), encoding="utf-8")
    result = magnification_result(
        magnification_id=mag_id,
        human_feedback_artifact_ref=human_feedback_artifact_ref,
        magnified_feedback_artifact_ref=str(magnified_path),
        metadata={"method": "stub", "count": 1},
    )
    result_path = root / f"{mag_id}.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if emit_ledger:
        try:
            from hg_core.ledger import emit
            emit(
                "MAGNIFICATION_COMPLETED",
                "magnification",
                mag_id,
                {"magnification_id": mag_id, "magnified_feedback_artifact_ref": str(magnified_path), "artifact_ref": str(result_path)},
                workspace_root=workspace_root,
                object_path=str(result_path),
            )
        except Exception:
            pass
    return result


def get_magnification_result(workspace_root: Path, magnification_id: str) -> Optional[MagnificationResult]:
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{magnification_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("magnification_id") == magnification_id and validate_magnification_result(data):
                    return data
            except Exception:
                continue
    return None
