"""
Anomaly detection: deterministic rules; emit ANOMALY_DETECTED with rationale artifact.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hg_core.ledger import emit
from ..artifacts import write_rationale_artifact


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def integrity_rule(observation: Dict[str, Any], workspace_root: Path) -> Optional[Dict[str, Any]]:
    """
    If payload_ref points to an artifact, verify file SHA-256 matches integrity.payload_sha256.
    Returns metrics dict if mismatch (anomaly); None if ok or no artifact.
    """
    ref = observation.get("payload_ref") or {}
    path_str = ref.get("path")
    expected_hex = (observation.get("integrity") or {}).get("payload_sha256")
    if not path_str or not expected_hex:
        return None
    p = Path(path_str)
    if not p.is_absolute() and workspace_root:
        p = Path(workspace_root) / p
    if not p.exists():
        return {"reason": "artifact_missing", "path": path_str}
    raw = p.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_hex:
        return {"reason": "integrity_mismatch", "expected": expected_hex, "actual": actual}
    return None


def expected_range_rule(
    observation: Dict[str, Any],
    _workspace_root: Path,
    *,
    expected_range: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    If observation has a numeric value and expected_range (min/max), check violation.
    expected_range can come from signal registry or be passed in.
    """
    if not expected_range:
        return None
    # expected_range may be passed via observation from registry
    er = observation.get("_expected_range") or expected_range
    if not er:
        return None
    payload_inline = observation.get("payload_inline") or {}
    value = payload_inline.get("value")
    if value is None:
        value = payload_inline.get("n")
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    lo = er.get("min")
    hi = er.get("max")
    if lo is not None and v < float(lo):
        return {"reason": "below_min", "value": v, "min": float(lo)}
    if hi is not None and v > float(hi):
        return {"reason": "above_max", "value": v, "max": float(hi)}
    return None


def detect_anomalies(
    observation_row: Dict[str, Any],
    rules: List[tuple],
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> List[str]:
    """
    Run rules; for each that returns metrics, write rationale artifact and emit ANOMALY_DETECTED.
    rules: list of (rule_id, severity, description, callable) where callable(obs, workspace_root) -> optional metrics dict.
    Returns list of anomaly_ids emitted.
    """
    workspace_root = Path(workspace_root or ".")
    out: List[str] = []
    ts = _iso_ts()
    obs_id = observation_row.get("observation_id", "")

    for rule_id, severity, description, fn in rules:
        if callable(fn):
            metrics = fn(observation_row, workspace_root)
        else:
            metrics = None
        if metrics is None:
            continue
        anomaly_id = hashlib.sha256(f"{obs_id}:{rule_id}:{ts}".encode()).hexdigest()
        rationale = {
            "anomaly_id": anomaly_id,
            "rule_id": rule_id,
            "severity": severity,
            "description": description,
            "metrics": metrics,
            "ts": ts,
        }
        write_rationale_artifact(workspace_root, anomaly_id, rationale, metadata={"signal_id": observation_row.get("signal_id", "")})
        emit(
            "ANOMALY_DETECTED",
            "anomaly",
            anomaly_id,
            {
                "anomaly_id": anomaly_id,
                "severity": severity,
                "rule_id": rule_id,
                "signal_id": observation_row.get("signal_id", ""),
                "observation_ids": [obs_id],
                "rationale_artifact_id": anomaly_id,
                "metrics": metrics,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        out.append(anomaly_id)
    return out
