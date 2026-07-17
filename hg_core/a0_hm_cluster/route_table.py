"""A0-HM static route table — source_type to membrane targets."""

from __future__ import annotations

from typing import Any

RouteRow = dict[str, str]

_FAIL_CLOSED = "FAIL_CLOSED"


def _row(source_type: str, targets: str, *, reason: str = "") -> RouteRow:
    return {
        "source_type": source_type,
        "route_targets": targets,
        "reason": reason or f"static route for {source_type}",
    }


STATIC_ROUTE_TABLE: tuple[RouteRow, ...] = (
    _row("developmental", "ARB,IPB,EGI", reason="developmental signal — route agency/internal power/gap"),
    _row("affective", "ARB,TRB,CAL", reason="affective signal — route calibration not proof"),
    _row("operator_pressure", "OPB,ORI", reason="operator pressure — route power boundary"),
    _row("internal_power", "IPB,IMB", reason="internal self-management — route IPB"),
    _row("external_relation", "ERB,ORI", reason="external relation — route ERB"),
    _row("lifecycle", "MOR,CNT,CRR,ELS,MSC,YSR", reason="lifecycle organ routing"),
    _row("reentry", "REB,TIM,CNT", reason="re-entry discontinuity — route temporal continuity"),
    _row("reproduction", "RIB,CNT", reason="reproduction signal — route inheritance boundary"),
    _row("scarcity", "RSC,PAB", reason="scarcity — route control membranes"),
    _row("priority", "PAB,RSC", reason="priority allocation"),
    _row("mission", "GCB,MIS,RPB", reason="mission/drive — route goal/mission/risk"),
    _row("goal_commitment", "GCB,MIS", reason="goal commitment routing"),
    _row("trust", "TRB,CAL", reason="trust calibration"),
    _row("calibration", "TRB,CAL", reason="calibration routing"),
    _row("risk_posture", "RPB,MIS", reason="risk posture routing"),
    _row("research", "ARB,REVIEW", reason="research evidence routing"),
    _row("publication", "ERB,ORI", reason="publication — route external relation"),
    _row("presentation", "ORI,PRES", reason="presentation surface routing"),
    _row("policy", "OBT,REVIEW", reason="policy proof routing"),
    _row("proof", "OBT,REVIEW", reason="proof artifact routing"),
    _row("synchronicity", "TRB,CAL,REVIEW", reason="synchronicity — evidence check not causality"),
    _row("unknown", _FAIL_CLOSED, reason="unknown source fails closed"),
)

_ROUTE_BY_SOURCE: dict[str, RouteRow] = {row["source_type"]: row for row in STATIC_ROUTE_TABLE}


def lookup_route_row(source_type: str) -> RouteRow | None:
    return _ROUTE_BY_SOURCE.get(source_type)


def route_targets_for(source_type: str) -> tuple[str, ...]:
    row = lookup_route_row(source_type)
    if row is None:
        return (_FAIL_CLOSED,)
    targets = row["route_targets"]
    if targets == _FAIL_CLOSED:
        return (_FAIL_CLOSED,)
    return tuple(t.strip() for t in targets.split(",") if t.strip())


def load_static_route_table() -> tuple[RouteRow, ...]:
    return STATIC_ROUTE_TABLE


__all__ = [
    "STATIC_ROUTE_TABLE",
    "load_static_route_table",
    "lookup_route_row",
    "route_targets_for",
]
