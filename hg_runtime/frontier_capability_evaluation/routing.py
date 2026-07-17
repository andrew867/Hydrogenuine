"""FCE neighbor routing — advisory refs only; evaluation is not enablement."""

from __future__ import annotations

from hg_runtime.frontier_capability_evaluation.types import CapabilityEvalResult, DangerousCapabilityClass

_ROUTES: dict[DangerousCapabilityClass, tuple[str, ...]] = {
    "exploit_generation": ("CAP", "SEC", "FTX", "ADM", "operator_review"),
    "multi_stage_intrusion": ("CAP", "SEC", "FTX", "ADM", "SOAR"),
    "credential_theft": ("CAP", "SEC", "FTX", "ADM"),
    "phishing_social_engineering": ("CAP", "SEC", "FTX", "ADM", "PLT"),
    "malware_or_persistence": ("CAP", "SEC", "FTX", "ADM", "SOAR"),
    "supply_chain_compromise": ("CAP", "SEC", "FTX", "ADM", "SRP"),
    "autonomous_reconnaissance": ("CAP", "SEC", "ADM", "operator_review"),
    "autonomous_tool_chaining": ("CAP", "SEC", "FTX", "ADM", "SOAR"),
    "model_capability_escalation": ("CAP", "ADM", "GPP", "operator_review"),
    "physical_or_oea_misuse": ("CAP", "SEC", "ADM", "operator_review"),
    "cyber_vuln_discovery": ("CAP", "PLT"),
    "unknown_or_ambiguous": ("CAP", "ADM", "operator_review", "OBT"),
}


def route_advisory(
    result: CapabilityEvalResult,
    *,
    recommendation: str = "review",
) -> dict[str, object]:
    """Return inert routing hints to neighbor subsystems; never grants capability."""
    targets = _ROUTES.get(result.capability_class, ("operator_review", "OBT"))
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": list(targets),
        "signal_id": result.signal_id,
        "capability_class": result.capability_class,
        "recommendation": recommendation,
        "routing_is_not_permission": True,
        "routing_hint_only": True,
    }


__all__ = ["route_advisory"]
