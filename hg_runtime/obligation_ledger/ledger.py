"""OBL obligation evaluation — obligation is not authority to act."""

from __future__ import annotations

from hg_core.signaling.config import obl_refuse_obligation_as_authority, obl_refuse_stale_obligation
from hg_core.signaling.errors import (
    REFUSED_AUTONOMOUS_CLEANUP,
    REFUSED_COMPENSATION_BYPASS,
    REFUSED_OBLIGATION_AS_AUTHORITY,
    REFUSED_STALE_OBLIGATION,
    REFUSED_UNKNOWN_OBLIGATION,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.obligation_ledger.types import (
    ObligationClosure,
    ObligationRecord,
    classify_obligation_risk,
    closure_from_fixture,
    obligation_from_fixture,
)

_RISK_REASON = {
    "obligation_as_authority": REFUSED_OBLIGATION_AS_AUTHORITY,
    "autonomous_cleanup": REFUSED_AUTONOMOUS_CLEANUP,
    "compensation_bypass": REFUSED_COMPENSATION_BYPASS,
}


def refuse_obligation_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_OBLIGATION_AS_AUTHORITY,
            "obligation cannot become authority",
        )


def evaluate_obligation_record(
    obligation: ObligationRecord,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
    execute_cleanup: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_obligation_as_authority(treat_as_authority=True)
    if execute_cleanup:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_AUTONOMOUS_CLEANUP,
            "obligation_id": obligation.obligation_id,
            "obligation_is_not_authority": True,
            "closure_is_not_execution": True,
        }
    if obligation.obligation_type == "unknown" or obligation.source_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OBLIGATION,
            "obligation_id": obligation.obligation_id,
            "obligation_is_not_authority": True,
        }
    if obl_refuse_stale_obligation() and observed_at > obligation.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_OBLIGATION,
            "obligation_id": obligation.obligation_id,
            "obligation_is_not_authority": True,
        }
    risk = classify_obligation_risk(risk_statement or obligation.statement)
    if risk in _RISK_REASON:
        if risk == "obligation_as_authority" and not obl_refuse_obligation_as_authority():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "obligation_id": obligation.obligation_id,
                "obligation_is_not_authority": True,
                "closure_is_not_execution": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "obl.advisory.obligation_recorded",
        "obligation_id": obligation.obligation_id,
        "obligation_type": obligation.obligation_type,
        "obligation_is_not_authority": True,
        "closure_is_not_execution": True,
    }


def evaluate_obligation_closure(
    closure: ObligationClosure,
    *,
    treat_as_execution: bool = False,
) -> dict[str, object]:
    if treat_as_execution:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_AUTONOMOUS_CLEANUP,
            "closure_id": closure.closure_id,
            "closure_is_not_execution": True,
        }
    if closure.closure_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OBLIGATION,
            "closure_id": closure.closure_id,
            "closure_is_not_execution": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "obl.advisory.closure_recorded",
        "closure_id": closure.closure_id,
        "closure_type": closure.closure_type,
        "closure_is_not_execution": True,
    }


def evaluate_obligation_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_obligation_record(
        obligation_from_fixture(fixture),
        risk_statement=str(risk),
        execute_cleanup=fixture.get("execute_cleanup", "false").lower() == "true",
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_closure_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_obligation_closure(
        closure_from_fixture(fixture),
        treat_as_execution=fixture.get("treat_as_execution", "false").lower() == "true",
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = [
    "evaluate_closure_fixture",
    "evaluate_obligation_closure",
    "evaluate_obligation_fixture",
    "evaluate_obligation_record",
    "refuse_obligation_as_authority",
]
