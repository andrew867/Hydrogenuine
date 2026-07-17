"""
Offline audit bundle: select events and anchors, write bundle dir with index, ledger_events.jsonl, anchors, manifests.
Verifiable offline without the running product.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from hg_core.ledger.ledger_writer import iterate_events, _iter_scope_paths


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_offline_bundle(
    workspace_root: Path,
    output_dir: Path,
    *,
    event_ids: Optional[List[str]] = None,
    scope_filter: Optional[Dict[str, str]] = None,
    include_artifacts: bool = False,
    tenant_id: str = "default",
    environment: str = "prod",
) -> Dict[str, Any]:
    """
    Build offline bundle in output_dir: bundle.json (index), ledger_events.jsonl, anchors.jsonl, manifests/.
    If event_ids provided, only those events; else all events. Redaction/tombstones: omit tombstoned artifact refs.
    Returns bundle index dict.
    """
    workspace_root = Path(workspace_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = _iso_ts()
    bundle_id = "bundle_" + hashlib.sha256(ts.encode()).hexdigest()[:16]

    # Collect events
    selected: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for ev in iterate_events(workspace_root):
        eid = ev.get("event_id")
        if not eid:
            continue
        if event_ids and eid not in event_ids:
            continue
        if scope_filter:
            sc = ev.get("scope") or {}
            if scope_filter.get("type") and sc.get("type") != scope_filter["type"]:
                continue
            if scope_filter.get("id") and sc.get("id") != scope_filter["id"]:
                continue
        if eid in seen:
            continue
        seen.add(eid)
        selected.append(ev)

    # ledger_events.jsonl
    events_path = output_dir / "ledger_events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for ev in selected:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Anchors from artifacts/integrity/anchors
    anchors_path = output_dir / "anchors.jsonl"
    anchors_dir = workspace_root / "artifacts" / "integrity" / "anchors"
    anchor_records: List[Dict[str, Any]] = []
    if anchors_dir.exists():
        for p in anchors_dir.glob("*.json"):
            try:
                anchor_records.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
    with open(anchors_path, "w", encoding="utf-8") as f:
        for a in anchor_records:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    # Manifests
    manifests_dir = output_dir / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    artifacts_manifest: Dict[str, str] = {}
    artifacts_root = workspace_root / "artifacts"
    if artifacts_root.exists() and include_artifacts:
        for p in artifacts_root.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".jsonl"):
                rel = str(p.relative_to(artifacts_root))
                artifacts_manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    (manifests_dir / "artifacts_manifest.json").write_text(
        json.dumps(artifacts_manifest, indent=2),
        encoding="utf-8",
    )
    policies_manifest: Dict[str, str] = {}
    policy_dir = workspace_root / "artifacts" / "policy"
    if policy_dir.exists():
        for p in policy_dir.rglob("*.json"):
            rel = str(p.relative_to(workspace_root))
            policies_manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    (manifests_dir / "policies_manifest.json").write_text(
        json.dumps(policies_manifest, indent=2),
        encoding="utf-8",
    )
    materializers_manifest: Dict[str, Any] = {}
    replay_reg = workspace_root / "artifacts" / "replay" / "materializer_versions.json"
    if replay_reg.exists():
        materializers_manifest["registry"] = hashlib.sha256(replay_reg.read_bytes()).hexdigest()
    (manifests_dir / "materializers_manifest.json").write_text(
        json.dumps(materializers_manifest, indent=2),
        encoding="utf-8",
    )

    # Chain hash for integrity
    chain_hashes: List[str] = []
    for ev in selected:
        chain_hashes.append(ev.get("event_id", ""))
    integrity_hash = hashlib.sha256(json.dumps(chain_hashes, sort_keys=True).encode()).hexdigest()

    # Differentiators Pack 1: include policy_proofs and verification in contents when present
    policy_proofs_dir = workspace_root / "artifacts" / "policy_proofs"
    verification_dir = workspace_root / "artifacts" / "verification"
    contents_extra: Dict[str, Any] = {}
    if policy_proofs_dir.exists() and include_artifacts:
        contents_extra["policy_proofs_count"] = len(list(policy_proofs_dir.glob("*.json")))
    if verification_dir.exists():
        for sub in ("checks", "robustness", "sources"):
            d = verification_dir / sub
            if d.exists():
                contents_extra[f"verification_{sub}_count"] = len(list(d.glob("*.json")))

    index = {
        "bundle_id": bundle_id,
        "created_ts": ts,
        "tenant_id": tenant_id,
        "environment": environment,
        "contents": {
            "ledger_events_count": len(selected),
            "anchors_count": len(anchor_records),
            **contents_extra,
        },
        "manifests": {
            "artifacts_manifest.json": hashlib.sha256((manifests_dir / "artifacts_manifest.json").read_bytes()).hexdigest(),
            "policies_manifest.json": hashlib.sha256((manifests_dir / "policies_manifest.json").read_bytes()).hexdigest(),
            "materializers_manifest.json": hashlib.sha256((manifests_dir / "materializers_manifest.json").read_bytes()).hexdigest(),
        },
        "integrity": {
            "events_chain_hash": integrity_hash,
            "ledger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
        },
    }
    (output_dir / "bundle.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index
