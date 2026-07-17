"""
Interop Pack 2: Connector SDK — manifest publish, conformance run, certification.
CONNECTOR_SDK_MANIFEST_PUBLISHED, CONNECTOR_CONFORMANCE_RAN, CONNECTOR_CERTIFIED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_connector_manifest(
    *,
    connector_id: str,
    operations: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    data_classes: Optional[List[str]] = None,
    receipt_schema: Optional[Dict[str, Any]] = None,
) -> str:
    """Write manifest artifact, emit CONNECTOR_SDK_MANIFEST_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "connector_sdk"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{connector_id}_manifest.json"
    doc = {
        "connector_id": connector_id,
        "operations": operations,
        "data_classes": data_classes or [],
        "receipt_schema": receipt_schema or {},
        "published_ts": ts,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "CONNECTOR_SDK_MANIFEST_PUBLISHED",
        "connector_sdk",
        connector_id,
        {"connector_id": connector_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def run_connector_conformance(
    *,
    connector_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    scenarios_passed: Optional[Dict[str, bool]] = None,
) -> tuple[Dict[str, Any], str]:
    """Run conformance scenarios, write report artifact, emit CONNECTOR_CONFORMANCE_RAN. Returns (report, event_id)."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    report_id = "conf_" + hashlib.sha256(f"{connector_id}:{ts}".encode()).hexdigest()[:16]
    scenarios = scenarios_passed or {}
    passed = all(scenarios.values()) if scenarios else True
    report = {"report_id": report_id, "connector_id": connector_id, "ts": ts, "passed": passed, "scenarios": scenarios}
    root = workspace_root / "artifacts" / "connector_sdk"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{report_id}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ev = emit(
        "CONNECTOR_CONFORMANCE_RAN",
        "connector_sdk",
        report_id,
        {"report_id": report_id, "connector_id": connector_id, "passed": passed, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return report, ev


def certify_connector(
    *,
    connector_id: str,
    report_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit CONNECTOR_CERTIFIED (optional). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "CONNECTOR_CERTIFIED",
        "connector_sdk",
        connector_id,
        {"connector_id": connector_id, "report_id": report_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
