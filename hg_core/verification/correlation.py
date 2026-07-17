"""
Pack 5: Verifier correlation — co-failure patterns, clusters, monoculture detection.
VERIFIER_CORRELATION_COMPUTED, VERIFIER_CLUSTER_UPDATED, VERIFIER_MONOCULTURE_DETECTED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_checks_by_action(workspace_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Group VERIFICATION_CHECK_PERFORMED by action_id."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    by_action: Dict[str, List[Dict[str, Any]]] = {}
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "VERIFICATION_CHECK_PERFORMED":
            continue
        p = ev.get("payload") or {}
        aid = p.get("action_id")
        if not aid:
            continue
        if aid not in by_action:
            by_action[aid] = []
        by_action[aid].append(p)
    return by_action


def _compute_cofailure_pairs(by_action: Dict[str, List[Dict[str, Any]]]) -> Dict[Tuple[str, str], int]:
    """Count (source_a, source_b) pairs that both failed on the same action. Symmetric."""
    pairs: Dict[Tuple[str, str], int] = {}
    for checks in by_action.values():
        failed_sources = [c.get("source_id") for c in checks if c.get("result") == "fail" and c.get("source_id")]
        failed_sources = list(dict.fromkeys(failed_sources))
        for i, a in enumerate(failed_sources):
            for b in failed_sources[i:]:
                if a == b:
                    key = (a, b)
                    pairs[key] = pairs.get(key, 0) + 1
                else:
                    k1, k2 = (a, b) if a < b else (b, a)
                    pairs[(k1, k2)] = pairs.get((k1, k2), 0) + 1
    return pairs


def _sources_from_artifacts(workspace_root: Path) -> List[str]:
    """List source_ids from artifacts."""
    root = workspace_root / "artifacts" / "verification" / "sources"
    if not root.exists():
        return []
    return [p.stem for p in root.glob("*.json")]


def compute_correlation(
    workspace_root: Path,
    domain: str = "default",
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
    """
    Compute correlation matrix (co-failure rate) and cluster assignments.
    Returns (matrix_by_source, cluster_by_source). cluster_by_source: source_id -> cluster_id.
    """
    by_action = _load_checks_by_action(workspace_root)
    pairs = _compute_cofailure_pairs(by_action)
    sources = _sources_from_artifacts(workspace_root)
    if not sources:
        return {}, {}
    # Fail count per source
    fail_count: Dict[str, int] = {s: 0 for s in sources}
    for checks in by_action.values():
        for c in checks:
            if c.get("result") == "fail":
                sid = c.get("source_id")
                if sid in fail_count:
                    fail_count[sid] += 1
    # Correlation: for (a,b) cofail / min(fail_a, fail_b) or 0
    matrix: Dict[str, Dict[str, float]] = {s: {s: 1.0} for s in sources}
    for (a, b), count in pairs.items():
        if a not in matrix or b not in matrix:
            continue
        denom = max(1, min(fail_count.get(a, 0), fail_count.get(b, 0)))
        corr = min(1.0, count / denom)
        matrix[a][b] = corr
        matrix[b][a] = corr
    # Simple clustering: high correlation -> same cluster (union-find style)
    parent: Dict[str, str] = {}
    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    threshold = 0.5
    for a in sources:
        for b in sources:
            if a >= b:
                continue
            if matrix.get(a, {}).get(b, 0) >= threshold:
                union(a, b)
    cluster_by_source = {s: find(s) for s in sources}
    return matrix, cluster_by_source


def emit_correlation_computed(
    *,
    domain: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """
    Compute correlation and clusters, write artifacts, emit VERIFIER_CORRELATION_COMPUTED.
    Returns (corr_id, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    matrix, clusters = compute_correlation(workspace_root, domain)
    ts = _iso_ts()
    corr_id = "corr_" + hashlib.sha256(f"{domain}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "verification" / "correlation"
    root.mkdir(parents=True, exist_ok=True)
    matrix_path = root / f"{corr_id}_matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    clusters_path = root / f"{corr_id}_clusters.json"
    clusters_path.write_text(json.dumps(clusters, indent=2), encoding="utf-8")
    ev_id = emit(
        "VERIFIER_CORRELATION_COMPUTED",
        "verifier_correlation",
        corr_id,
        {
            "corr_id": corr_id,
            "domain": domain,
            "ts": ts,
            "matrix_artifact_id": str(matrix_path),
            "clusters_artifact_id": str(clusters_path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return corr_id, ev_id


def update_clusters_and_emit(
    *,
    domain: str,
    cluster_by_source: Dict[str, str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write cluster artifact and emit VERIFIER_CLUSTER_UPDATED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "verification" / "clusters"
    root.mkdir(parents=True, exist_ok=True)
    cluster_id = "clu_" + hashlib.sha256(f"{domain}:{ts}".encode()).hexdigest()[:16]
    path = root / f"{cluster_id}.json"
    path.write_text(json.dumps({"cluster_id": cluster_id, "domain": domain, "cluster_by_source": cluster_by_source, "ts": ts}, indent=2), encoding="utf-8")
    return emit(
        "VERIFIER_CLUSTER_UPDATED",
        "verifier_cluster",
        cluster_id,
        {"cluster_id": cluster_id, "domain": domain, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def check_monoculture(
    workspace_root: Path,
    source_ids: List[str],
    domain: str = "default",
    threshold_same_cluster_ratio: float = 1.0,
) -> bool:
    """
    Return True if selected sources are monoculture (all from same cluster).
    If cluster data missing, treat as single cluster -> True when len(source_ids) > 1.
    """
    if len(source_ids) <= 1:
        return False
    _, cluster_by_source = compute_correlation(workspace_root, domain)
    if not cluster_by_source:
        return True
    clusters_used: Set[str] = set()
    for sid in source_ids:
        clusters_used.add(cluster_by_source.get(sid, sid))
    return len(clusters_used) == 1


def emit_monoculture_detected(
    *,
    action_id: str,
    source_ids: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    domain: str = "default",
) -> str:
    """Emit VERIFIER_MONOCULTURE_DETECTED (triggers safeguard). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "VERIFIER_MONOCULTURE_DETECTED",
        "verifier_correlation",
        action_id,
        {"action_id": action_id, "source_ids": source_ids, "domain": domain, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
