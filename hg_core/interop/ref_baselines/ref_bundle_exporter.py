"""
Interop Pack 6: Reference bundle exporter — produces minimal audit bundle (bundle.json, events.jsonl, manifests/).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def export_toy_bundle(
    out_dir: Path,
    *,
    extra_events: Optional[List[Dict[str, Any]]] = None,
    bundle_id_prefix: str = "toy-bundle",
) -> Dict[str, Any]:
    """
    Create minimal reference bundle in out_dir:
    - bundle.json (index)
    - events.jsonl
    - manifests/artifacts_manifest.json
    Returns bundle index dict.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifests").mkdir(parents=True, exist_ok=True)
    ts = _iso_ts()
    events = [
        {"event_id": "e1", "action": "WORK_ITEM_CREATED", "ts": ts, "payload": {"title": "Toy scenario"}},
        {"event_id": "e2", "action": "ACTION_PROPOSED", "ts": ts, "payload": {"tool": "ref_connector.op"}},
    ]
    if extra_events:
        events.extend(extra_events)
    events_path = out_dir / "events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    artifacts_manifest: List[Dict[str, Any]] = []
    manifests_path = out_dir / "manifests" / "artifacts_manifest.json"
    with open(manifests_path, "w", encoding="utf-8") as f:
        json.dump(artifacts_manifest, f, indent=2)
    bundle_id = bundle_id_prefix + "_" + hashlib.sha256(ts.encode()).hexdigest()[:12]
    bundle = {
        "bundle_id": bundle_id,
        "created_ts": ts,
        "contents": {"events": "events.jsonl", "manifests": "manifests/"},
    }
    bundle_path = out_dir / "bundle.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
    return bundle
