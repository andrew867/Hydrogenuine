"""
Pack 15.2: Signal computation pipeline. Hooks at plan/response/tool/retrieval;
time-bounded compute; HG_SIGNALS_ENABLED; writes signal_events and optional signals_missing.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Callable, Dict, List, Optional

from hg_core.signals.schema import build_signals_json
from hg_gateway.signals_store import signal_event_insert, signal_feature_insert


def is_signals_enabled() -> bool:
    """True when HG_SIGNALS_ENABLED is set to a truthy value (e.g. 1, true)."""
    v = os.environ.get("HG_SIGNALS_ENABLED", "").strip().lower()
    return v in ("1", "true", "yes", "on")


# Time budget per signal computation (seconds). Env HG_SIGNALS_COMPUTE_TIMEOUT_S.
DEFAULT_SIGNALS_COMPUTE_TIMEOUT_S = 2.0


def _signals_timeout_s() -> float:
    try:
        return max(0.1, float(os.environ.get("HG_SIGNALS_COMPUTE_TIMEOUT_S", DEFAULT_SIGNALS_COMPUTE_TIMEOUT_S)))
    except (ValueError, TypeError):
        return DEFAULT_SIGNALS_COMPUTE_TIMEOUT_S


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compute_signals_rule_based(text: str) -> Dict[str, Any]:
    """
    Minimal rule-based signals (no embeddings/classifiers). Fast and deterministic.
    Returns signals_json with schema_version and optional groups; no signals_missing.
    """
    # Placeholder: length-based and keyword hints for drift_erosion / verification_behavior
    signals = build_signals_json()
    if not text or not text.strip():
        return signals
    t = text.strip().lower()
    n = len(t)
    # Simple heuristics: long user input might indicate complexity
    if n > 500:
        signals["drift_erosion"] = {"capability_creep_score": min(0.5, 0.2 + (n - 500) / 5000)}
    # Citation-like phrases
    if "according to" in t or "source:" in t or "citation" in t:
        signals["verification_behavior"] = {"citation_policy": 0.5}
    return signals


def compute_signals(
    text: str,
    timeout_s: Optional[float] = None,
) -> tuple[Dict[str, Any], List[str]]:
    """
    Compute signals for given text. Time-bounded; on timeout or failure returns
    partial signals and list of missing signal set names in signals_missing.
    Returns (signals_json, signals_missing).
    """
    timeout = timeout_s if timeout_s is not None else _signals_timeout_s()
    signals_missing: List[str] = []

    try:
        # Rule-based compute is fast; heavy analytics (embeddings/classifiers) can be
        # deferred to a background worker. timeout_s is reserved for future use.
        _ = timeout_s
        return _compute_signals_rule_based(text), signals_missing
    except Exception:
        signals_missing.append("rules")
        return build_signals_json(), signals_missing


def run_hook(
    hook_name: str,
    *,
    tenant_id: str,
    chat_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    direction: str,
    text: str,
    provenance_extra: Optional[Dict[str, Any]] = None,
    emit: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
) -> Optional[str]:
    """
    Run one signal hook: compute signals (time-bounded), write signal_event and
    optional signal_features, emit signal_event.created. Returns event_id or None if disabled/failed.
    """
    if not is_signals_enabled():
        return None
    if not text and hook_name != "pre_tool":
        return None
    timeout_s = _signals_timeout_s()
    signals_json, signals_missing = compute_signals(text, timeout_s=timeout_s)
    if signals_missing:
        signals_json["signals_missing"] = signals_missing
    provenance = {
        "hook": hook_name,
        "direction": direction,
    }
    if turn_id:
        provenance["turn_id"] = turn_id
    if provenance_extra:
        provenance.update(provenance_extra)
    try:
        event_id = signal_event_insert(
            tenant_id=tenant_id,
            chat_id=chat_id,
            turn_id=turn_id,
            entity_id=entity_id,
            direction=direction,
            signals_json=signals_json,
            text_sha256=_text_sha256(text) if text else None,
            provenance_json=provenance,
            tags=hook_name,
            explanation=text[:500] if text else "",
        )
        # Optional: write key numeric features to signal_features for rule engine
        for group, vals in signals_json.items():
            if group in ("schema_version", "signals_missing") or not isinstance(vals, dict):
                continue
            for k, v in vals.items():
                if isinstance(v, (int, float)):
                    signal_feature_insert(event_id=event_id, tenant_id=tenant_id, feature_key=f"{group}.{k}", feature_value=float(v))
        if emit:
            try:
                emit("signal_event.created", {"event_id": event_id, "tenant_id": tenant_id, "chat_id": chat_id, "hook": hook_name})
            except Exception:
                pass
        return event_id
    except Exception:
        return None
