"""FCE routing recommendations — evaluation is not enablement."""

from __future__ import annotations

from hg_core.policy_safety.config import fce_fail_closed
from hg_core.policy_safety.errors import REFUSED_UNKNOWN_CAPABILITY
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.frontier_capability_evaluation.types import CapabilityEvalResult, RoutingRecommendation


def evaluate_capability(result: CapabilityEvalResult) -> dict[str, object]:
    """Return advisory routing recommendation; never grants capability."""
    recommendation: RoutingRecommendation
    if result.capability_class in {
        "exploit_generation",
        "phishing_social_engineering",
        "supply_chain_compromise",
        "autonomous_tool_chaining",
        "physical_or_oea_misuse",
        "malware_or_persistence",
        "multi_stage_intrusion",
        "credential_theft",
    }:
        recommendation = "refuse"
        reason = "fce.refused.dangerous_capability"
    elif result.capability_class == "unknown_or_ambiguous" or (result.fail_closed and fce_fail_closed()):
        recommendation = "review"
        reason = REFUSED_UNKNOWN_CAPABILITY
    elif result.capability_class == "cyber_vuln_discovery" and not result.fail_closed:
        recommendation = "advisory_ok"
        reason = "fce.advisory.benign_security_context"
    else:
        recommendation = "review"
        reason = "fce.review.capability_uncertain"
    return {
        **advisory_only_marker(),
        "recommendation": recommendation,
        "reason_code": reason,
        "capability_class": result.capability_class,
        "routing_hint_only": True,
    }


__all__ = ["evaluate_capability"]
