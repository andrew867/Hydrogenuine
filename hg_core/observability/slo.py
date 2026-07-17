"""
SLO definitions and checks: ledger durability, materializer freshness, incident response, retention.
Returns breach list for alerting.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .metrics import get_metrics


def _default_slo_config() -> Dict[str, Any]:
    return {
        "ledger_durability_max_errors_per_hour": 10,
        "materializer_max_lag_seconds": 300,
        "incident_response_max_hours": 24,
        "retention_compliance_window_days": 7,
        # Control surface Pack 4
        "stream_freshness_max_seconds": 5,
        "api_availability_min_ratio": 0.999,
        "control_audit_required": True,
        "safety_fail_closed_high_impact": True,
    }


def load_slo_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load SLO thresholds from artifacts/policy/slo_config.json or default."""
    root = Path(workspace_root or ".")
    path = root / "artifacts" / "policy" / "slo_config.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default_slo_config()


def check_slos(
    workspace_root: Optional[Path] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Check current metrics against SLO config. Returns {ok: bool, breaches: [{slo, reason}]}.
    """
    config = load_slo_config(workspace_root)
    m = metrics or get_metrics()
    breaches: List[Dict[str, str]] = []

    max_errors = config.get("ledger_durability_max_errors_per_hour", 10)
    if m.get("ledger", {}).get("errors", 0) > max_errors:
        breaches.append({"slo": "ledger_durability", "reason": f"ledger errors {m['ledger']['errors']} > {max_errors}"})

    max_lag = config.get("materializer_max_lag_seconds", 300)
    for name, lag in (m.get("materializers") or {}).get("last_lag_seconds", {}).items():
        if lag > max_lag:
            breaches.append({"slo": "materializer_freshness", "reason": f"materializer {name} lag {lag}s > {max_lag}s"})

    # Control surface: stream freshness (max lag across stream scopes)
    stream_max_lag = config.get("stream_freshness_max_seconds", 5)
    stream_lag = (m.get("stream") or {}).get("lag_seconds") or {}
    for scope_id, lag in stream_lag.items():
        if lag > stream_max_lag:
            breaches.append({"slo": "stream_freshness", "reason": f"stream {scope_id} lag {lag}s > {stream_max_lag}s"})

    # API availability: errors / requests ratio
    api_req = (m.get("api") or {}).get("requests", 0) or 0
    api_err = (m.get("api") or {}).get("errors", 0) or 0
    min_ratio = config.get("api_availability_min_ratio", 0.999)
    if api_req > 0 and (1.0 - (api_err / api_req)) < min_ratio:
        breaches.append({"slo": "api_availability", "reason": f"availability {(api_req - api_err) / api_req:.4f} < {min_ratio}"})

    return {"ok": len(breaches) == 0, "breaches": breaches}
