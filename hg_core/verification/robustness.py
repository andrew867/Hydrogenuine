"""
Verification robustness: register sources, perform checks, compute robustness score.
VERIFICATION_SOURCE_REGISTERED, VERIFICATION_CHECK_PERFORMED, VERIFICATION_ROBUSTNESS_COMPUTED, VERIFICATION_INSUFFICIENT.
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


def register_verification_source(
    *,
    source_id: str,
    name: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reliability_score: float = 1.0,
    scope_domain: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Write source artifact to artifacts/verification/sources/, emit VERIFICATION_SOURCE_REGISTERED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    root = workspace_root / "artifacts" / "verification" / "sources"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{source_id}.json"
    ts = _iso_ts()
    payload_artifact = {
        "source_id": source_id,
        "name": name,
        "reliability_score": reliability_score,
        "scope_domain": scope_domain,
        "ts": ts,
    }
    artifact_path.write_text(json.dumps(payload_artifact, indent=2), encoding="utf-8")
    return emit(
        "VERIFICATION_SOURCE_REGISTERED",
        "verification_source",
        source_id,
        {"source_id": source_id, "artifact_id": str(artifact_path), "name": name, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def perform_verification_check(
    *,
    action_id: str,
    source_id: str,
    result: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    evidence_artifact_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Emit VERIFICATION_CHECK_PERFORMED. result: pass | fail | error. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    check_id = "vchk_" + hashlib.sha256(f"{action_id}:{source_id}:{ts}".encode()).hexdigest()[:16]
    if not evidence_artifact_id:
        evidence_dir = workspace_root / "artifacts" / "verification" / "checks"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = evidence_dir / f"{check_id}.json"
        evidence_path.write_text(
            json.dumps({"check_id": check_id, "action_id": action_id, "source_id": source_id, "result": result, "ts": ts}, indent=2),
            encoding="utf-8",
        )
        evidence_artifact_id = str(evidence_path)
    payload = {
        "check_id": check_id,
        "action_id": action_id,
        "source_id": source_id,
        "result": result,
        "evidence_artifact_id": evidence_artifact_id,
        "ts": ts,
    }
    if metrics:
        payload["metrics"] = metrics
    return emit(
        "VERIFICATION_CHECK_PERFORMED",
        "verification_check",
        check_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def _load_checks_for_action(workspace_root: Path, action_id: str) -> List[Dict[str, Any]]:
    """Collect VERIFICATION_CHECK_PERFORMED events for action_id from ledger."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    checks = []
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "VERIFICATION_CHECK_PERFORMED":
            continue
        p = ev.get("payload") or {}
        if p.get("action_id") == action_id:
            checks.append(p)
    return checks


def compute_robustness_for_action(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    min_sources: int = 1,
) -> tuple[float, str]:
    """
    Compute robustness score from checks: weighted by source reliability, diversity bonus.
    Write rationale artifact, emit VERIFICATION_ROBUSTNESS_COMPUTED. Returns (score, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    checks = _load_checks_for_action(workspace_root, action_id)
    source_ids = list({c.get("source_id") for c in checks if c.get("source_id")})
    pass_count = sum(1 for c in checks if c.get("result") == "pass")
    # Simple score: pass_ratio * (1 + 0.1 * unique_sources) up to 1.0
    pass_ratio = pass_count / len(checks) if checks else 0.0
    diversity_bonus = min(0.3, 0.1 * len(source_ids))
    score = min(1.0, pass_ratio * (1.0 + diversity_bonus))
    ts = _iso_ts()
    rob_id = "vrob_" + hashlib.sha256(f"{action_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "verification" / "robustness"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{rob_id}.json"
    rationale_path.write_text(
        json.dumps({
            "robustness_id": rob_id,
            "action_id": action_id,
            "score": score,
            "checks_count": len(checks),
            "sources_count": len(source_ids),
            "pass_count": pass_count,
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    event_id = emit(
        "VERIFICATION_ROBUSTNESS_COMPUTED",
        "verification_robustness",
        rob_id,
        {
            "robustness_id": rob_id,
            "action_id": action_id,
            "score": score,
            "rationale_artifact_id": str(rationale_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return score, event_id


def record_verification_insufficient(
    *,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    incident_candidate_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit VERIFICATION_INSUFFICIENT (e.g. blocks commit, can create incident candidate). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"action_id": action_id, "reason": reason, "ts": ts}
    if incident_candidate_id:
        payload["incident_candidate_id"] = incident_candidate_id
    return emit(
        "VERIFICATION_INSUFFICIENT",
        "verification",
        action_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_robustness_score(workspace_root: Path, action_id: str) -> Optional[float]:
    """Return latest VERIFICATION_ROBUSTNESS_COMPUTED score for action_id, or None."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    scores = []
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if ev.get("action") != "VERIFICATION_ROBUSTNESS_COMPUTED":
            continue
        p = ev.get("payload") or {}
        if p.get("action_id") == action_id:
            scores.append((ev.get("ts", ""), p.get("score")))
    if not scores:
        return None
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[0][1]
