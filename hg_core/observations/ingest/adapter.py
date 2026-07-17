"""
Observation ingest: write artifact, emit OBSERVATION_RECORDED.
Supports HTTP (fetch URL) and inline payload (for file/log/metric adapters and tests).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from hg_core.ledger import emit
from ..registry import SignalRegistry
from ..artifacts import write_observation_artifact


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _compute_observation_id(signal_id: str, payload_sha256: str, ts: str) -> str:
    return hashlib.sha256(f"{signal_id}:{payload_sha256}:{ts}".encode()).hexdigest()


def ingest_observation(
    workspace_root: Path,
    signal_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    registry: SignalRegistry,
    *,
    payload_bytes: Optional[bytes] = None,
    source: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
    timeout_s: int = 10,
) -> str:
    """
    Ingest one observation: resolve signal, obtain payload (from url or payload_bytes),
    write artifact, emit OBSERVATION_RECORDED. Returns observation_id.
    """
    workspace_root = Path(workspace_root)
    sd = registry.get(signal_id)
    ts = _iso_ts()

    if payload_bytes is not None:
        raw = payload_bytes
        source_info = source or {"type": "inline", "ts": ts}
    elif url is not None:
        try:
            req = Request(url, headers={"User-Agent": "Hydrogenuine-Observation/1.0"})
            with urlopen(req, timeout=timeout_s) as r:
                raw = r.read()
                status = getattr(r, "status", 200)
                content_type = r.headers.get("Content-Type") if hasattr(r, "headers") else None
            source_info = {"type": "http", "url": url, "status": status, "content_type": content_type}
        except (URLError, HTTPError, OSError) as e:
            raw = b""
            source_info = {"type": "http", "url": url, "error": str(e), "status": -1}
    else:
        schema_url = sd.schema.get("x_url") if isinstance(sd.schema, dict) else None
        if schema_url:
            try:
                req = Request(schema_url, headers={"User-Agent": "Hydrogenuine-Observation/1.0"})
                with urlopen(req, timeout=timeout_s) as r:
                    raw = r.read()
                    status = getattr(r, "status", 200)
                    content_type = r.headers.get("Content-Type") if hasattr(r, "headers") else None
                source_info = {"type": "http", "url": schema_url, "status": status, "content_type": content_type}
            except (URLError, HTTPError, OSError) as e:
                raw = b""
                source_info = {"type": "http", "url": schema_url, "error": str(e), "status": -1}
        else:
            raw = b""
            source_info = source or {"type": "inline"}

    payload_sha256 = hashlib.sha256(raw).hexdigest()
    observation_id = _compute_observation_id(signal_id, payload_sha256, ts)

    ext = "bin"
    content_type = source_info.get("content_type")
    if content_type and "json" in content_type:
        ext = "json"

    art = write_observation_artifact(
        workspace_root,
        observation_id,
        raw,
        ext=ext,
        content_type=content_type,
        metadata={"signal_id": signal_id},
    )

    completeness = 1.0 if (raw and (source_info.get("status", 0) in (200, None))) else 0.0
    if source_info.get("error"):
        completeness = 0.0

    payload_event = {
        "observation_id": observation_id,
        "signal_id": signal_id,
        "ts_observed": ts,
        "ts_ingested": ts,
        "source": source_info,
        "pii_class": getattr(sd, "pii_class", "none"),
        "payload_ref": {
            "path": art["path"],
            "checksum": art["checksum"],
            "size_bytes": art["size_bytes"],
        },
        "integrity": {
            "payload_sha256": payload_sha256,
            "content_type": content_type,
            "size_bytes": len(raw),
        },
        "quality": {
            "reliability": sd.reliability,
            "completeness": completeness,
            "parse_errors": [],
        },
        "labels": [],
    }

    emit(
        "OBSERVATION_RECORDED",
        "observation",
        observation_id,
        payload_event,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
        object_path=art["path"],
    )
    return observation_id
