"""
Observation indexer: from OBSERVATION_RECORDED, OBSERVATION_TRANSFORMED, OBSERVATION_BOUND, ANOMALY_DETECTED
build materialized index for fast list/detail/filter API.
Output: observations.jsonl, transforms.jsonl, bindings.jsonl, anomalies.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    observations_path = root / "observations.jsonl"
    transforms_path = root / "transforms.jsonl"
    bindings_path = root / "bindings.jsonl"
    anomalies_path = root / "anomalies.jsonl"
    checkpoint: Dict[str, str] = {}
    observations: List[Dict[str, Any]] = []
    transforms: List[Dict[str, Any]] = []
    bindings: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        base = {
            "event_id": ev.get("event_id"),
            "ts": ts,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "agent_id": actor.get("agent_id", ""),
        }
        if action == "OBSERVATION_RECORDED":
            observations.append({
                **base,
                "observation_id": payload.get("observation_id", ""),
                "signal_id": payload.get("signal_id", ""),
                "pii_class": payload.get("pii_class", "none"),
                "ts_observed": payload.get("ts_observed", ""),
                "ts_ingested": payload.get("ts_ingested", ""),
                "source": payload.get("source", {}),
                "payload_ref": payload.get("payload_ref", {}),
                "payload_inline": payload.get("payload_inline"),
                "integrity": payload.get("integrity", {}),
                "quality": payload.get("quality", {}),
                "labels": payload.get("labels", []),
            })
        elif action == "OBSERVATION_TRANSFORMED":
            transforms.append({
                **base,
                "transform_id": payload.get("transform_id", ev.get("object", {}).get("id", "")),
                "observation_id": payload.get("observation_id", ""),
                "derived_observation_id": payload.get("derived_observation_id", ""),
                "transform_type": payload.get("transform_type", ""),
            })
        elif action == "OBSERVATION_BOUND":
            bindings.append({
                **base,
                "observation_id": payload.get("observation_id", ""),
                "entity_id": payload.get("entity_id"),
                "claim_id": payload.get("claim_id"),
                "field_path": payload.get("field_path"),
                "confidence": payload.get("confidence", 1.0),
                "method": payload.get("method", "rule"),
                "rationale_artifact_id": payload.get("rationale_artifact_id"),
            })
        elif action == "ANOMALY_DETECTED":
            anomalies.append({
                **base,
                "anomaly_id": payload.get("anomaly_id", ev.get("object", {}).get("id", "")),
                "severity": payload.get("severity", ""),
                "rule_id": payload.get("rule_id", ""),
                "signal_id": payload.get("signal_id", ""),
                "observation_ids": payload.get("observation_ids", []),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
                "metrics": payload.get("metrics", {}),
            })

    with open(observations_path, "w", encoding="utf-8") as f:
        for r in observations:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(transforms_path, "w", encoding="utf-8") as f:
        for r in transforms:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(bindings_path, "w", encoding="utf-8") as f:
        for r in bindings:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(anomalies_path, "w", encoding="utf-8") as f:
        for r in anomalies:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "observations", checkpoint)
