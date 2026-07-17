"""
Pack4: Enforce tenant quotas at gateway: rate, streams, tool concurrency, chats, messages, storage.
On exceed: emit quota.exceeded audit event and return 429/403 with structured body and Retry-After where applicable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from hg_core.tenancy.quotas import (
    QuotaLimits,
    QuotaUsage,
    check_chats,
    check_messages,
    check_rate,
    check_storage,
    check_streams,
    check_tool_runs,
)
from hg_core.tenancy.quotas import check_pending_approvals as _check_pending_approvals


def _current_minute() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def _get_limits(store: Any, tenant_id: str) -> QuotaLimits:
    raw = store.quota_get(tenant_id) if hasattr(store, "quota_get") else None
    return QuotaLimits.from_dict(raw)


def _get_usage(store: Any, tenant_id: str) -> QuotaUsage:
    raw = store.usage_get(tenant_id) if hasattr(store, "usage_get") else {}
    return QuotaUsage.from_dict(raw)


def _effective_usage(store: Any, tenant_id: str) -> QuotaUsage:
    """Merge stored usage with live counts from store (chat_count, message_count, pending_approvals)."""
    u = _get_usage(store, tenant_id)
    if hasattr(store, "chat_list"):
        u.chat_count = len(store.chat_list(tenant_id))
    if hasattr(store, "chat_list"):
        total_msgs = 0
        for c in store.chat_list(tenant_id):
            cid = c.get("chat_id")
            if cid:
                total_msgs += len(store.message_list(tenant_id, cid))
        u.message_count = total_msgs
    if hasattr(store, "approval_list"):
        pending = [a for a in store.approval_list(tenant_id) if (a or {}).get("status") == "pending"]
        u.pending_approvals = len(pending)
    return u


def _emit_quota_exceeded(store: Any, tenant_id: str, code: str, detail: Dict[str, Any]) -> None:
    if hasattr(store, "audit_append"):
        store.audit_append(
            tenant_id,
            "quota.exceeded",
            {"quota_code": code, "detail": detail},
        )


def check_request_rate(store: Any, tenant_id: str) -> Tuple[bool, str, int]:
    """
    Check request rate limit. Returns (allowed, quota_code, retry_after_seconds).
    If allowed, caller should call consume_request_rate afterward.
    """
    limits = _get_limits(store, tenant_id)
    usage = _get_usage(store, tenant_id)
    current_minute = _current_minute()
    allowed, reason = check_rate(limits, usage, current_minute)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, "rate_exceeded", {"limit": limits.request_per_minute})
        return False, "rate_exceeded", 60
    return True, "ok", 0


def consume_request_rate(store: Any, tenant_id: str) -> None:
    """Increment rate count for current minute. Call after check_request_rate allows."""
    usage = _get_usage(store, tenant_id)
    current_minute = _current_minute()
    if usage.rate_minute != current_minute:
        usage.rate_minute = current_minute
        usage.rate_count = 0
    usage.rate_count += 1
    if hasattr(store, "usage_set"):
        store.usage_set(tenant_id, usage.to_dict())


def check_chat_create(store: Any, tenant_id: str) -> Tuple[bool, str]:
    limits = _get_limits(store, tenant_id)
    usage = _effective_usage(store, tenant_id)
    allowed, reason = check_chats(limits, usage)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, reason, {"limit": limits.max_chats})
        return False, reason
    return True, "ok"


def check_message_add(store: Any, tenant_id: str, chat_id: str) -> Tuple[bool, str]:
    limits = _get_limits(store, tenant_id)
    usage = _effective_usage(store, tenant_id)
    messages_in_chat = len(store.message_list(tenant_id, chat_id)) if hasattr(store, "message_list") else 0
    allowed, reason = check_messages(limits, usage, messages_in_chat=messages_in_chat)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, reason, {"limit_total": limits.max_messages_total, "limit_per_chat": limits.max_messages_per_chat})
        return False, reason
    return True, "ok"


def check_stream_enter(store: Any, tenant_id: str) -> Tuple[bool, str]:
    limits = _get_limits(store, tenant_id)
    usage = _get_usage(store, tenant_id)
    allowed, reason = check_streams(limits, usage)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, reason, {"limit": limits.concurrent_streams})
        return False, reason
    return True, "ok"


def consume_stream_enter(store: Any, tenant_id: str) -> None:
    usage = _get_usage(store, tenant_id)
    usage.active_streams = usage.active_streams + 1
    if hasattr(store, "usage_set"):
        store.usage_set(tenant_id, usage.to_dict())


def release_stream(store: Any, tenant_id: str) -> None:
    usage = _get_usage(store, tenant_id)
    usage.active_streams = max(0, usage.active_streams - 1)
    if hasattr(store, "usage_set"):
        store.usage_set(tenant_id, usage.to_dict())


def check_tool_run_start(store: Any, tenant_id: str) -> Tuple[bool, str]:
    limits = _get_limits(store, tenant_id)
    usage = _get_usage(store, tenant_id)
    allowed, reason = check_tool_runs(limits, usage)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, reason, {"limit": limits.concurrent_tool_runs})
        return False, reason
    return True, "ok"


def consume_tool_run_start(store: Any, tenant_id: str) -> None:
    usage = _get_usage(store, tenant_id)
    usage.active_tool_runs = usage.active_tool_runs + 1
    if hasattr(store, "usage_set"):
        store.usage_set(tenant_id, usage.to_dict())


def release_tool_run(store: Any, tenant_id: str) -> None:
    usage = _get_usage(store, tenant_id)
    usage.active_tool_runs = max(0, usage.active_tool_runs - 1)
    if hasattr(store, "usage_set"):
        store.usage_set(tenant_id, usage.to_dict())


def check_storage_add(store: Any, tenant_id: str, additional_bytes: int = 0) -> Tuple[bool, str]:
    limits = _get_limits(store, tenant_id)
    usage = _effective_usage(store, tenant_id)
    allowed, reason = check_storage(limits, usage, additional_bytes=additional_bytes)
    if not allowed:
        _emit_quota_exceeded(store, tenant_id, reason, {"limit": limits.max_artifact_bytes})
        return False, reason
    return True, "ok"


def get_tenant_limits_and_usage(store: Any, tenant_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (limits_dict, usage_dict) for tenant. For GET /v1/tenants/me and /usage."""
    limits = _get_limits(store, tenant_id)
    usage = _effective_usage(store, tenant_id)
    return limits.to_dict(), usage.to_dict()
