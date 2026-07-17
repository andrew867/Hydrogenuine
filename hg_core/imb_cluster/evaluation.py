"""IMB cluster evaluation helpers — advisory-only, explicit containment paths."""

from __future__ import annotations

from collections.abc import Callable

from hg_core.imb_cluster.no_authority import advisory_only_marker

ADVISORY_MARKER_KEYS = frozenset(
    {"advisory_only", "permission_granted", "authority_created", "mediation_is_advisory_only"}
)


def assert_advisory_result(result: dict[str, object]) -> None:
    marker = advisory_only_marker()
    for key, expected in marker.items():
        if result.get(key) is not expected:
            raise AssertionError(f"expected {key}={expected!r}, got {result.get(key)!r}")


def resolve_risk_containment(
    *,
    risk: str | None,
    risk_reason_map: dict[str, str],
    waived_reason_code: str,
    payload: dict[str, object],
    refuse_for_risk: Callable[[str], bool] | None = None,
) -> dict[str, object] | None:
    if not risk or risk not in risk_reason_map:
        return None
    refuse_enabled = refuse_for_risk(risk) if refuse_for_risk is not None else True
    if refuse_enabled:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": risk_reason_map[risk],
            "observed_risk": risk,
            "containment_active": True,
            **payload,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": waived_reason_code,
        "observed_risk": risk,
        "would_contain_reason_code": risk_reason_map[risk],
        "containment_refuse_disabled": True,
        "containment_waived": True,
        **payload,
    }


__all__ = [
    "ADVISORY_MARKER_KEYS",
    "assert_advisory_result",
    "resolve_risk_containment",
]
