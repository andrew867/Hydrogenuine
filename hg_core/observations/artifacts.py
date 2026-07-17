"""
Observation artifact storage: raw payloads and rationale blobs under artifacts/observations/.
Returns path and SHA-256 checksum for ledger provenance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _observations_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "observations"


def _date_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_observation_artifact(
    workspace_root: Path,
    observation_id: str,
    content: bytes,
    *,
    ext: str = "bin",
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Write raw observation payload to artifacts/observations/raw/<date>/<observation_id>.<ext>.
    Returns {"path": str, "checksum": "sha256:hex", "size_bytes": int}.
    """
    root = _observations_root(workspace_root) / "raw" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{observation_id}.{ext}"
    path.write_bytes(content)
    checksum = _sha256_hex(content)
    return {
        "path": str(path),
        "checksum": f"sha256:{checksum}",
        "payload_sha256": checksum,
        "size_bytes": len(content),
        "content_type": content_type,
    }


def write_rationale_artifact(
    workspace_root: Path,
    artifact_id: str,
    obj: Dict[str, Any],
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Write rationale (e.g. anomaly) JSON to artifacts/observations/derived/<date>/<artifact_id>.json.
    Returns {"path": str, "checksum": "sha256:hex", "artifact_id": str}.
    """
    root = _observations_root(workspace_root) / "derived" / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{artifact_id}.json"
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    checksum = _sha256_hex(raw)
    return {
        "path": str(path),
        "checksum": f"sha256:{checksum}",
        "artifact_id": artifact_id,
    }
