"""
Layer 8 Phase 3: Storage and API for representation interpretability inspection results.
Persist InspectionResult to run_dir and/or global store; query by run_id/decision_id/node_id;
proof-path export reads from global store by decision_id.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _repr_interp_artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "repr_interp"


def _global_results_path(workspace_root: Path) -> Path:
    """Path to global repr_interp results index (for proof-path lookup by decision_id)."""
    return _repr_interp_artifacts_root(Path(workspace_root)) / "results.jsonl"


def _append_result(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def store_inspection_result(
    workspace_root: Path,
    result: Dict[str, Any],
    run_dir: Optional[Path] = None,
) -> None:
    """
    Store an inspection result for later retrieval and proof-path emission.
    - If run_dir is set, appends to run_dir/repr_interp_results.jsonl.
    - If result has decision_id, also appends to global store (artifacts/repr_interp/results.jsonl)
      so get_proof_path can include it via representation_inspection_result.
    result should contain at least: prompt_id, output_text; and optionally inspection_id (or request_id),
    decision_id, run_id, node_id, artifact_ref, ts/created_at, etc.
    """
    workspace_root = Path(workspace_root)
    record = dict(result)
    if not record.get("created_at") and not record.get("ts"):
        record["created_at"] = datetime.now(timezone.utc).isoformat()
    if record.get("request_id") and not record.get("inspection_id"):
        record["inspection_id"] = record["request_id"]
    if run_dir is not None:
        run_path = Path(run_dir) / "repr_interp_results.jsonl"
        _append_result(run_path, record)
    if record.get("decision_id"):
        global_path = _global_results_path(workspace_root)
        _append_result(global_path, record)


def get_inspection_results(
    workspace_root: Path,
    run_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    node_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return inspection results from run_dir (if provided) and/or global store, filtered by
    run_id, decision_id, node_id. Used by API and by get_proof_path for representation_inspection_result.
    """
    workspace_root = Path(workspace_root)
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def add_from_path(path: Path) -> None:
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if run_id is not None and r.get("run_id") != run_id:
                    continue
                if decision_id is not None and r.get("decision_id") != decision_id:
                    continue
                if node_id is not None and r.get("node_id") != node_id:
                    continue
                key = (r.get("inspection_id") or r.get("request_id"), r.get("created_at") or r.get("ts"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(r)

    if run_dir is not None:
        add_from_path(Path(run_dir) / "repr_interp_results.jsonl")
    if decision_id is not None or run_id is not None or node_id is not None:
        add_from_path(_global_results_path(workspace_root))

    return out


def write_inspection_artifact(workspace_root: Path, inspection_id: str, result: Dict[str, Any]) -> str:
    """
    Write full inspection result to artifacts/repr_interp/results_artifacts/<date>/<inspection_id>.json.
    Returns the artifact path string for use as artifact_ref in store_inspection_result.
    """
    workspace_root = Path(workspace_root)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _repr_interp_artifacts_root(workspace_root) / "results_artifacts" / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{inspection_id}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def read_run_dir_results(run_dir: Path) -> List[Dict[str, Any]]:
    """Read all inspection results from run_dir/repr_interp_results.jsonl (for tests)."""
    path = Path(run_dir) / "repr_interp_results.jsonl"
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
