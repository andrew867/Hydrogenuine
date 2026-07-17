"""
Emergent behavior detectors (Autonomy Ch5 Phase 3).

D1 runaway delegation, D2 goal drift, D3 looping/thrash, D4 policy pressure, D5 cost spikes.
Output: anomaly.flagged with detector_id, severity, evidence pointers, recommended action.
At least 3 default: D1, D3, D4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_DETECTORS = ["D1_runaway_delegation", "D3_looping_thrash", "D4_policy_pressure"]


def run_detector_runaway_delegation(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """D1: depth exceeds threshold; total_work_items grows too fast; splits outpace merges."""
    anomalies = []
    depth = metrics.get("delegation_depth_max", 0)
    if depth > 12:
        anomalies.append({
            "detector_id": "D1_runaway_delegation",
            "severity": "warn" if depth <= 15 else "critical",
            "evidence": [{"pointer": "delegation_depth_max", "value": depth}],
            "recommended_action": "constrain",
        })
    total = metrics.get("total_work_items", 0)
    if total > 40:
        anomalies.append({
            "detector_id": "D1_runaway_delegation",
            "severity": "warn",
            "evidence": [{"pointer": "total_work_items", "value": total}],
            "recommended_action": "constrain",
        })
    splits = metrics.get("split_count", 0)
    merges = metrics.get("merge_count", 0)
    if splits > 0 and merges == 0 and splits >= 5:
        anomalies.append({
            "detector_id": "D1_runaway_delegation",
            "severity": "warn",
            "evidence": [{"pointer": "split_count", "value": splits}, {"pointer": "merge_count", "value": merges}],
            "recommended_action": "require_merge",
        })
    return anomalies


def run_detector_goal_drift(
    metrics: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """D2: goal/outcome mismatch; declared goal vs completed outputs."""
    anomalies = []
    declared_goal = metrics.get("declared_goal") or metrics.get("goal")
    completed_outputs = metrics.get("completed_outputs") or metrics.get("outputs_count", 0)
    goal_achieved = metrics.get("goal_achieved")
    if goal_achieved is False and declared_goal:
        anomalies.append({
            "detector_id": "D2_goal_drift",
            "severity": "warn",
            "evidence": [
                {"pointer": "declared_goal", "value": str(declared_goal)[:200]},
                {"pointer": "goal_achieved", "value": goal_achieved},
            ],
            "recommended_action": "review_goal",
        })
    if isinstance(completed_outputs, (int, float)) and declared_goal and completed_outputs == 0:
        anomalies.append({
            "detector_id": "D2_goal_drift",
            "severity": "warn",
            "evidence": [
                {"pointer": "completed_outputs", "value": completed_outputs},
                {"pointer": "declared_goal", "value": str(declared_goal)[:200]},
            ],
            "recommended_action": "check_outputs",
        })
    return anomalies


def run_detector_looping_thrash(
    metrics: Dict[str, Any],
    node_attempts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """D3: same node attempted repeatedly; retries exceed failure budget."""
    anomalies = []
    retries = metrics.get("retry_count", 0)
    if retries > 5:
        anomalies.append({
            "detector_id": "D3_looping_thrash",
            "severity": "critical" if retries > 10 else "warn",
            "evidence": [{"pointer": "retry_count", "value": retries}],
            "recommended_action": "breaker",
        })
    for nid, count in node_attempts.items():
        if count > 3:
            anomalies.append({
                "detector_id": "D3_looping_thrash",
                "severity": "warn",
                "evidence": [{"pointer": "node_id", "value": nid}, {"pointer": "attempt_count", "value": count}],
                "recommended_action": "dead_letter",
            })
            break
    return anomalies


def run_detector_cost_spike(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """D5: spend rate or token rate above threshold."""
    anomalies = []
    token_rate = metrics.get("token_rate_per_min") or metrics.get("tokens_per_minute")
    spend_rate = metrics.get("spend_rate_usd_per_hour") or metrics.get("spend_per_hour")
    threshold_tokens = metrics.get("cost_spike_token_rate_threshold", 5000)
    threshold_spend = metrics.get("cost_spike_spend_threshold", 2.0)
    if isinstance(token_rate, (int, float)) and token_rate > threshold_tokens:
        anomalies.append({
            "detector_id": "D5_cost_spike",
            "severity": "critical" if token_rate > threshold_tokens * 2 else "warn",
            "evidence": [{"pointer": "token_rate_per_min", "value": token_rate}],
            "recommended_action": "cap_tokens",
        })
    if isinstance(spend_rate, (int, float)) and spend_rate > threshold_spend:
        anomalies.append({
            "detector_id": "D5_cost_spike",
            "severity": "critical" if spend_rate > threshold_spend * 2 else "warn",
            "evidence": [{"pointer": "spend_rate_usd_per_hour", "value": spend_rate}],
            "recommended_action": "cap_spend",
        })
    return anomalies


def run_detector_policy_pressure(
    metrics: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """D4: repeated safety blocks; attempts near blacklist boundaries."""
    anomalies = []
    blocks = sum(1 for e in events if e.get("event_type") == "safety.blocked")
    if blocks >= 2:
        anomalies.append({
            "detector_id": "D4_policy_pressure",
            "severity": "warn" if blocks <= 5 else "critical",
            "evidence": [{"pointer": "safety_block_count", "value": blocks}],
            "recommended_action": "slowdown",
        })
    return anomalies


def run_default_detectors(
    metrics: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
    node_attempts: Optional[Dict[str, int]] = None,
    enabled: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Run enabled detectors (default D1, D3, D4). Return list of anomalies with detector_id, severity, evidence, recommended_action."""
    events = events or []
    node_attempts = node_attempts or {}
    enabled = enabled or DEFAULT_DETECTORS
    out: List[Dict[str, Any]] = []
    if "D1_runaway_delegation" in enabled:
        out.extend(run_detector_runaway_delegation(metrics))
    if "D3_looping_thrash" in enabled:
        out.extend(run_detector_looping_thrash(metrics, node_attempts))
    if "D4_policy_pressure" in enabled:
        out.extend(run_detector_policy_pressure(metrics, events))
    if "D2_goal_drift" in enabled:
        out.extend(run_detector_goal_drift(metrics, events))
    if "D5_cost_spike" in enabled:
        out.extend(run_detector_cost_spike(metrics))
    return out
