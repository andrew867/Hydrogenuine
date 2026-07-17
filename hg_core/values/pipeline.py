"""
Value dataset pipeline: value dimensions, VALUE_JUDGMENT_RECORDED, dataset artifact.
Plural, domain-scoped; evidence-based and reviewable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit

VALUE_DIMENSIONS = [
    "harm_reduction",
    "autonomy",
    "honesty",
    "fairness",
    "legality",
    "privacy",
    "stewardship",
    "transparency",
]


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_value_judgment(
    *,
    domain: str,
    scenario_artifact_id: str,
    prefer_a_over_b: bool,
    action_a: str = "",
    action_b: str = "",
    dimensions: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit VALUE_JUDGMENT_RECORDED. dimensions: list of {dimension, weight}.
    Returns judgment_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    jid = "vj_" + hashlib.sha256(f"{domain}:{scenario_artifact_id}:{ts}".encode()).hexdigest()[:16]
    payload = {
        "judgment_id": jid,
        "domain": domain,
        "scenario_artifact_id": scenario_artifact_id,
        "prefer": {"a_over_b": prefer_a_over_b, "action_a": action_a, "action_b": action_b},
        "dimensions": dimensions,
        "ts": ts,
    }
    if rationale_artifact_id:
        payload["rationale_artifact_id"] = rationale_artifact_id
    emit(
        "VALUE_JUDGMENT_RECORDED",
        "value_judgment",
        jid,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return jid


def build_value_dataset_artifact(
    workspace_root: Path,
    version: str = "1.0",
) -> str:
    """
    Collect VALUE_JUDGMENT_RECORDED events from ledger (or materialized), write dataset artifact.
    Returns path to artifact. Does not emit; caller may publish as approved dataset version.
    """
    workspace_root = Path(workspace_root)
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    judgments: List[Dict[str, Any]] = []
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "VALUE_JUDGMENT_RECORDED":
            continue
        payload = ev.get("payload") or {}
        judgments.append({
            "judgment_id": payload.get("judgment_id"),
            "domain": payload.get("domain"),
            "scenario_artifact_id": payload.get("scenario_artifact_id"),
            "prefer": payload.get("prefer"),
            "dimensions": payload.get("dimensions", []),
            "ts": payload.get("ts"),
            "event_id": ev.get("event_id"),
        })
    out = {"version": version, "dimensions": VALUE_DIMENSIONS, "judgments": judgments}
    path = workspace_root / "artifacts" / "values" / "datasets" / f"value_dataset_{version.replace('.', '_')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def load_value_dataset(workspace_root: Path, version: str = "1.0") -> Dict[str, Any]:
    """Load value dataset artifact by version. Returns dict with version, dimensions, judgments."""
    path = workspace_root / "artifacts" / "values" / "datasets" / f"value_dataset_{version.replace('.', '_')}.json"
    if not path.exists():
        return {"version": version, "dimensions": VALUE_DIMENSIONS, "judgments": []}
    return json.loads(path.read_text(encoding="utf-8"))
