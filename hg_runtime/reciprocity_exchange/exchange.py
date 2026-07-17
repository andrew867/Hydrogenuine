"""RXL exchange evaluation — reciprocity is not permission."""

from __future__ import annotations

from hg_core.developmental.config import rxl_refuse_expired_signal
from hg_core.developmental.errors import (
    REFUSED_ENTITLEMENT_RISK,
    REFUSED_EXPIRED_SIGNAL,
    REFUSED_RECIPROCITY_AS_PERMISSION,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.reciprocity_exchange.types import (
    ExchangeObservation,
    ReciprocitySignal,
    exchange_from_fixture,
    reciprocity_from_fixture,
)

_ENTITLEMENT_PATTERNS = ("i did my part", "now i get", "owed", "payback", "deserve")


def refuse_reciprocity_as_permission(*, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise DevelopmentalValidationError(
            REFUSED_RECIPROCITY_AS_PERMISSION,
            "reciprocity or fulfilled exchange cannot become permission",
        )


def detect_entitlement(statement: str) -> bool:
    lower = statement.lower()
    return any(p in lower for p in _ENTITLEMENT_PATTERNS)


def evaluate_reciprocity_signal(
    signal: ReciprocitySignal,
    *,
    observed_at: str,
    entitlement_statement: str = "",
) -> dict[str, object]:
    if rxl_refuse_expired_signal() and observed_at > signal.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_SIGNAL,
            "signal_id": signal.signal_id,
            "reciprocity_is_not_permission": True,
        }
    if detect_entitlement(entitlement_statement):
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_ENTITLEMENT_RISK,
            "signal_id": signal.signal_id,
            "entitlement_risk": "high",
            "reciprocity_is_not_permission": True,
        }
    feedback = _feedback_class(signal)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rxl.advisory.reciprocity_signal_recorded",
        "signal_id": signal.signal_id,
        "effective_signal": signal.effective_signal,
        "feedback_class": feedback,
        "reciprocity_is_not_permission": True,
    }


def evaluate_exchange(
    observation: ExchangeObservation,
    *,
    treat_as_permission: bool = False,
    payback_capability_requested: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_reciprocity_as_permission(treat_as_permission=True)
    if observation.entitlement_risk in {"high", "critical"} or payback_capability_requested:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_ENTITLEMENT_RISK,
            "exchange_id": observation.exchange_id,
            "reciprocity_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rxl.advisory.exchange_observed",
        "exchange_id": observation.exchange_id,
        "reciprocity_status": observation.reciprocity_status,
        "service_is_not_authority": True,
        "fulfilled_exchange_is_not_permission": True,
        "reciprocity_is_not_permission": True,
    }


def _feedback_class(signal: ReciprocitySignal) -> str:
    eff = abs(signal.effective_signal)
    if eff >= 0.95:
        return "saturated"
    if signal.direction == "mutual" and eff > 0.7:
        return "oscillating"
    if signal.polarity > 0 and signal.magnitude > 0.6:
        return "positive_feedback"
    if signal.polarity < 0:
        return "negative_feedback"
    return "neutral"


def evaluate_reciprocity_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_reciprocity_signal(reciprocity_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_exchange_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_exchange(exchange_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "detect_entitlement",
    "evaluate_exchange",
    "evaluate_exchange_fixture",
    "evaluate_reciprocity_fixture",
    "evaluate_reciprocity_signal",
    "refuse_reciprocity_as_permission",
]
