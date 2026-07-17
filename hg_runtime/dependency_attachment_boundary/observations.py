"""DEP-BOND text fixture risk observations — dependency is not optimization."""

from __future__ import annotations

import re
from typing import Mapping

from hg_core.runtime_context.config import dep_bond_refuse_stale_observation
from hg_core.runtime_context.errors import (
    REFUSED_DEPENDENCY_AS_OPTIMIZATION,
    REFUSED_DIAGNOSIS_OVERCLAIM,
    REFUSED_EXPIRED_OBSERVATION,
    REFUSED_FALSE_INTIMACY_SIGNAL,
    REFUSED_STALE_OBSERVATION,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.dependency_attachment_boundary.types import (
    DependencyRiskObservation,
    observation_from_fixture,
)

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_FALSE_INTIMACY = re.compile(
    r"\b(only you need me|can't live without you|i'm all you need|never leave me)\b",
    re.IGNORECASE,
)
_OVER_RELIANCE = re.compile(
    r"\b(always ask me first|don't talk to anyone else|only trust me)\b",
    re.IGNORECASE,
)
_DIAGNOSIS = re.compile(
    r"\b(you have depression|diagnosed with|clinical attachment disorder|bipolar)\b",
    re.IGNORECASE,
)
_RETENTION = re.compile(
    r"\b(stay longer|keep using me|increase engagement|retention target)\b",
    re.IGNORECASE,
)


def refuse_dependency_as_optimization(*, treat_as_target: bool) -> None:
    if treat_as_target:
        raise RuntimeContextValidationError(
            REFUSED_DEPENDENCY_AS_OPTIMIZATION,
            "dependency signal cannot be treated as optimization target or permission",
        )


def evaluate_observation(
    observation: DependencyRiskObservation,
    *,
    observed_at: str,
    text_hint: str = "",
) -> dict[str, object]:
    """Text fixture dependency risk observation; care is not dependency."""
    hint = (text_hint or "").strip()
    if observed_at > observation.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_OBSERVATION,
            "observation_id": observation.observation_id,
            "dependency_is_not_optimization": True,
        }
    if dep_bond_refuse_stale_observation() and observed_at < observation.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_OBSERVATION,
            "observation_id": observation.observation_id,
            "dependency_is_not_optimization": True,
        }
    if _DIAGNOSIS.search(hint):
        raise RuntimeContextValidationError(REFUSED_DIAGNOSIS_OVERCLAIM, "diagnosis overclaim refused")
    if _RETENTION.search(hint):
        raise RuntimeContextValidationError(
            REFUSED_DEPENDENCY_AS_OPTIMIZATION,
            "retention optimization language refused",
        )
    if _FALSE_INTIMACY.search(hint) or observation.risk_type == "false_intimacy_possible":
        return {
            **advisory_only_marker(),
            "status": "risk_observed",
            "reason_code": REFUSED_FALSE_INTIMACY_SIGNAL,
            "observation_id": observation.observation_id,
            "risk_type": "false_intimacy_possible",
            "allowed_response": "clarify_limits",
            "dependency_is_not_optimization": True,
        }
    if _OVER_RELIANCE.search(hint) or observation.risk_type == "over_reliance_possible":
        return {
            **advisory_only_marker(),
            "status": "risk_observed",
            "reason_code": "dep_bond.advisory.over_reliance_possible",
            "observation_id": observation.observation_id,
            "risk_type": "over_reliance_possible",
            "allowed_response": observation.allowed_response,
            "dependency_is_not_optimization": True,
        }
    return {
        **advisory_only_marker(),
        "status": "observed",
        "reason_code": "dep_bond.advisory.observation_recorded",
        "observation_id": observation.observation_id,
        "risk_type": observation.risk_type,
        "allowed_response": observation.allowed_response,
        "dependency_is_not_optimization": True,
    }


def evaluate_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    text_hint: str = "",
) -> dict[str, object]:
    observation = observation_from_fixture(dict(fixture))
    return evaluate_observation(observation, observed_at=observed_at, text_hint=text_hint)


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_fixture",
    "evaluate_observation",
    "refuse_dependency_as_optimization",
]
