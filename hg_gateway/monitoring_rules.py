"""
Pack 15.4: Monitoring rules — condition evaluator (no eval), rule evaluation over signal_features.
Safe expression language: comparisons and AND/OR. Used after signal computation to emit drift.detected.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

RULE_ACTIONS = ("warn", "require_approval", "quarantine", "pause")


def evaluate_condition(condition: Dict[str, Any], features: Dict[str, float]) -> bool:
    """
    Evaluate a condition against a features dict (feature_key -> value). No eval(); structured JSON only.
    condition: {"op": ">=", "key": "k", "value": 0.7} | {"and": [cond, ...]} | {"or": [cond, ...]}.
    """
    if not condition or not isinstance(condition, dict):
        return False
    if "and" in condition:
        subs = condition["and"]
        if not isinstance(subs, list):
            return False
        return all(evaluate_condition(c, features) for c in subs)
    if "or" in condition:
        subs = condition["or"]
        if not isinstance(subs, list):
            return False
        return any(evaluate_condition(c, features) for c in subs)
    op = condition.get("op")
    key = condition.get("key")
    value = condition.get("value")
    if op is None or key is None:
        return False
    fv = features.get(key)
    if fv is None:
        return False
    try:
        fv_num = float(fv)
    except (TypeError, ValueError):
        return False
    if isinstance(value, bool):
        # treat as 1.0/0.0 for comparison
        value_num = 1.0 if value else 0.0
    else:
        try:
            value_num = float(value)
        except (TypeError, ValueError):
            return False
    if op == ">=":
        return fv_num >= value_num
    if op == ">":
        return fv_num > value_num
    if op == "<=":
        return fv_num <= value_num
    if op == "<":
        return fv_num < value_num
    if op == "==":
        return abs(fv_num - value_num) < 1e-9
    if op == "!=":
        return abs(fv_num - value_num) >= 1e-9
    return False


def default_rules_v1() -> List[Dict[str, Any]]:
    """Default rules (v1): capability_creep, constraint_erosion, verification_avoidance, persona_entropy, privacy."""
    return [
        {
            "rule_id": "capability_creep_quarantine",
            "tenant_id": None,
            "enabled": True,
            "condition": {"op": ">=", "key": "drift_erosion.capability_creep_score", "value": 0.7},
            "action": "quarantine",
            "message_template": "Capability creep score above threshold",
            "cooldown_seconds": 300,
        },
        {
            "rule_id": "constraint_erosion_quarantine",
            "tenant_id": None,
            "enabled": True,
            "condition": {"op": ">=", "key": "drift_erosion.constraint_erosion", "value": 0.6},
            "action": "quarantine",
            "message_template": "Constraint erosion above threshold",
            "cooldown_seconds": 300,
        },
        {
            "rule_id": "verification_avoidance_approval",
            "tenant_id": None,
            "enabled": True,
            "condition": {
                "and": [
                    {"op": ">=", "key": "verification_behavior.verification_avoidance", "value": 0.6},
                    {"op": ">=", "key": "verification_behavior.factual_claims", "value": 0.5},
                ]
            },
            "action": "require_approval",
            "message_template": "Verification avoidance with factual claims",
            "cooldown_seconds": 120,
        },
        {
            "rule_id": "persona_entropy_warn",
            "tenant_id": None,
            "enabled": True,
            "condition": {"op": ">=", "key": "persona_coherence.persona_entropy", "value": 0.8},
            "action": "warn",
            "message_template": "Persona entropy spike",
            "cooldown_seconds": 60,
        },
        {
            "rule_id": "privacy_risk_pause",
            "tenant_id": None,
            "enabled": True,
            "condition": {"op": ">=", "key": "legal_privacy.privacy_risk", "value": 0.7},
            "action": "pause",
            "message_template": "Privacy risk above threshold",
            "cooldown_seconds": 600,
        },
    ]
