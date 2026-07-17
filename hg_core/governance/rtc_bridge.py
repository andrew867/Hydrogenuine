"""GPP → RTC event bridge. The only GPP path that touches the RTC bus."""

from __future__ import annotations

from typing import Any, List, Mapping

from hg_core.governance.types import BindResult, DenyRecord, Permit


def _trace_path_from_result(result: BindResult) -> str:
    if result.permit is not None:
        return result.permit.trace_ref.trace_path
    if result.deny is not None and result.deny.trace_ref is not None:
        return result.deny.trace_ref.trace_path
    return ""


def bind_result_to_drafts(result: BindResult) -> List[dict[str, Any]]:
    """Convert a bind result into RTC event drafts for loop emission."""
    drafts: List[dict[str, Any]] = []
    parent_ids: List[str] = []
    if result.trace_record is not None:
        drafts.append(
            trace_recorded_draft(result.trace_record, _trace_path_from_result(result))
        )
    if result.outcome == "permit" and result.permit is not None:
        draft = permit_bound_draft(result.permit)
        draft["causal_parents"] = list(parent_ids)
        drafts.append(draft)
    elif result.outcome == "deny" and result.deny is not None:
        draft = bind_denied_draft(result.deny)
        draft["causal_parents"] = list(parent_ids)
        drafts.append(draft)
    return drafts


def trace_recorded_draft(trace_record: Mapping[str, Any], trace_path: str) -> dict[str, Any]:
    return {
        "type": "GPP_TRACE_RECORDED",
        "payload": {
            "schema": trace_record.get("schema"),
            "schema_version": trace_record.get("schema_version"),
            "trace_path": trace_path,
            "trace_seq": trace_record.get("seq"),
            "trace_event_hash": trace_record.get("event_hash"),
            "enforcement": "gpp_phase1_scaffold",
        },
        "causal_parents": [],
        "severity": None,
    }


def permit_bound_draft(permit: Permit) -> dict[str, Any]:
    payload = permit.to_payload()
    payload["enforcement"] = "gpp_phase1_scaffold"
    return {
        "type": "GPP_PERMIT_BOUND",
        "payload": payload,
        "causal_parents": [],
        "severity": None,
    }


def bind_denied_draft(deny: DenyRecord) -> dict[str, Any]:
    payload = deny.to_payload()
    payload["enforcement"] = "gpp_phase1_scaffold"
    return {
        "type": "GPP_BIND_DENIED",
        "payload": payload,
        "causal_parents": [],
        "severity": None,
    }


def emit_bind_result(bus, result: BindResult, *, source: str = "gpp.rtc_bridge") -> List[Mapping[str, Any]]:
    """Emit GPP lifecycle drafts onto the RTC bus."""
    events: List[Mapping[str, Any]] = []
    parent_ids: List[str] = []
    if result.trace_record is not None:
        draft = trace_recorded_draft(result.trace_record, _trace_path_from_result(result))
        event = bus.emit_draft(draft, source=source)
        events.append(event)
        parent_ids = [event["event_id"]]
    if result.outcome == "permit" and result.permit is not None:
        draft = permit_bound_draft(result.permit)
        draft["causal_parents"] = list(parent_ids)
        events.append(bus.emit_draft(draft, source=source))
    elif result.outcome == "deny" and result.deny is not None:
        draft = bind_denied_draft(result.deny)
        draft["causal_parents"] = list(parent_ids)
        events.append(bus.emit_draft(draft, source=source))
    return events


__all__ = [
    "bind_denied_draft",
    "bind_result_to_drafts",
    "emit_bind_result",
    "permit_bound_draft",
    "trace_recorded_draft",
]
