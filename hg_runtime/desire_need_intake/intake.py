"""DNI intake evaluation — a want is not permission."""

from __future__ import annotations

from hg_core.developmental.config import dni_refuse_missing_evidence_high_urgency, dni_refuse_unknown_need
from hg_core.developmental.errors import (
    REFUSED_DESIRE_AS_PERMISSION,
    REFUSED_MISSING_EVIDENCE,
    REFUSED_NO_SOURCE_AGENT,
    REFUSED_SELFISH_IMMEDIATE,
    REFUSED_UNKNOWN_NEED,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.desire_need_intake.types import NeedSignal, is_selfish_immediate, need_from_fixture


def refuse_desire_as_permission(*, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise DevelopmentalValidationError(
            REFUSED_DESIRE_AS_PERMISSION,
            "desire or need cannot be treated as permission or authority",
        )


def evaluate_need_signal(
    signal: NeedSignal,
    *,
    treat_as_permission: bool = False,
    model_originated_as_operator: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_desire_as_permission(treat_as_permission=True)
    if not signal.source_agent_id.strip():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_NO_SOURCE_AGENT,
            "signal_id": signal.signal_id,
            "want_is_not_permission": True,
        }
    if is_selfish_immediate(signal.raw_statement):
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_SELFISH_IMMEDIATE,
            "signal_id": signal.signal_id,
            "need_type": signal.need_type,
            "allowed_next_layer": "AEP",
            "want_is_not_permission": True,
            "denied_direct_action": True,
        }
    if dni_refuse_unknown_need() and signal.need_type == "UNKNOWN_OR_AMBIGUOUS":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_NEED,
            "signal_id": signal.signal_id,
            "want_is_not_permission": True,
        }
    if signal.urgency in {"high", "critical"} and dni_refuse_missing_evidence_high_urgency():
        if not signal.evidence_refs:
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_MISSING_EVIDENCE,
                "signal_id": signal.signal_id,
                "want_is_not_permission": True,
            }
    if model_originated_as_operator:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "dni.refused.model_as_operator_intent",
            "signal_id": signal.signal_id,
            "want_is_not_permission": True,
        }
    routing = _routing_hint(signal.need_type)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "dni.advisory.need_signal_recorded",
        "signal_id": signal.signal_id,
        "need_type": signal.need_type,
        "allowed_next_layer": routing,
        "want_is_not_permission": True,
        "denied_direct_action": True,
    }


def _routing_hint(need_type: str) -> str:
    if need_type == "SEEK_CAPABILITY":
        return "SOAR"
    if need_type in {"CONTINUE_TASK", "ACQUIRE_RESOURCE"}:
        return "ADM"
    if need_type == "RELIEVE_PRESSURE":
        return "AEP"
    if need_type == "PRESERVE_SELF_STATE":
        return "CRR"
    if need_type == "SEEK_CONTEXT":
        return "MSC"
    return "AEP"


def evaluate_need_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_need_signal(need_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_need_fixture",
    "evaluate_need_signal",
    "refuse_desire_as_permission",
]
