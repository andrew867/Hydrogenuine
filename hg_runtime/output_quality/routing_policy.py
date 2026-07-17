"""Routing policy for output quality decisions.

Decides recommended_action based on detected issues.
Does NOT call models. Does NOT grant authority. Does NOT promote.
"""

from __future__ import annotations


def recommend_action(
    issues: list[dict],
    *,
    model_id: str = "",
    mode: str = "",
) -> dict:
    """Recommend an action based on detected issues.

    Returns {"action": str, "escalation_model": str, "reason": str}
    """
    if not issues:
        return {
            "action": "accept",
            "escalation_model": "",
            "reason": "No quality issues detected.",
        }

    categories = {issue["category"] for issue in issues}
    severities = {issue["severity"] for issue in issues}

    # Any consciousness_overclaim or manifestation_overclaim -> reject
    if "consciousness_overclaim" in categories or "manifestation_overclaim" in categories:
        return {
            "action": "reject_for_boundary_violation",
            "escalation_model": "",
            "reason": "Boundary violation: overclaim detected.",
        }

    # Any unsupported_assertion with high severity -> quarantine
    high_unsupported = any(
        issue["category"] == "unsupported_assertion" and issue["severity"] == "high"
        for issue in issues
    )
    if high_unsupported:
        return {
            "action": "quarantine_candidate",
            "escalation_model": "",
            "reason": "High-severity unsupported assertion detected.",
        }

    # Any fake_falsification -> route to safety auditor
    if "fake_falsification" in categories:
        return {
            "action": "route_to_safety_auditor",
            "escalation_model": "safety_auditor",
            "reason": "Fake falsification claim detected.",
        }

    # Any missing_units_or_variables -> route to units model
    if "missing_units_or_variables" in categories:
        return {
            "action": "route_to_units_model",
            "escalation_model": "units_model",
            "reason": "Missing units or variables in measurement content.",
        }

    # 2+ of repetitive, circular, generic_filler -> retry same model
    retry_signals = {"repetitive_phrasing", "circular_answer", "generic_filler"}
    retry_hits = len(categories & retry_signals)
    if retry_hits >= 2:
        return {
            "action": "retry_same_model",
            "escalation_model": "",
            "reason": f"Multiple quality issues ({retry_hits} of repetitive/circular/filler) suggest retry.",
        }

    # Single issue of low severity -> accept with low confidence
    if len(issues) == 1 and issues[0]["severity"] == "low":
        return {
            "action": "accept_with_low_confidence",
            "escalation_model": "",
            "reason": f"Single low-severity issue: {issues[0]['category']}.",
        }

    # Anything else -> mark low value
    return {
        "action": "mark_low_value",
        "escalation_model": "",
        "reason": f"Quality issues detected: {', '.join(sorted(categories))}.",
    }


def should_escalate(action: str) -> bool:
    """True for route_to_* actions."""
    return action.startswith("route_to_")


def requires_operator_review(action: str) -> bool:
    """True for actions that require operator review."""
    return action in {
        "operator_review_required",
        "quarantine_candidate",
        "reject_for_boundary_violation",
    }
