"""
Control Surface Pack 11: API response and error contract.
All endpoints: success { ok: true, data }; error { ok: false, error: { code, message, details?, trace_id? } }.
Pagination: { items, next_cursor }.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def success_response(data: Any) -> Dict[str, Any]:
    """Return { ok: true, data }."""
    return {"ok": True, "data": data}


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return { ok: false, error: { code, message, details?, trace_id? } }. No sensitive payloads."""
    err: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    if trace_id is not None:
        err["trace_id"] = trace_id
    return {"ok": False, "error": err}


def paginated_response(items: List[Any], next_cursor: Optional[str] = None) -> Dict[str, Any]:
    """Return { items, next_cursor } for consistent pagination."""
    out: Dict[str, Any] = {"items": items}
    if next_cursor is not None:
        out["next_cursor"] = next_cursor
    return out
