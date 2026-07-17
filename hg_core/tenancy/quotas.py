"""
Pack4: Tenant resource quotas — limits, usage counters, and deterministic check helpers.
Persistence is in the gateway store (tenant_quotas / tenant_usage tables).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class QuotaLimits:
    """Per-tenant quota limits. None means no limit for that dimension."""

    request_per_minute: Optional[int] = None
    concurrent_streams: Optional[int] = None
    concurrent_tool_runs: Optional[int] = None
    max_chats: Optional[int] = None
    max_messages_per_chat: Optional[int] = None
    max_messages_total: Optional[int] = None
    max_artifact_bytes: Optional[int] = None
    max_pending_approvals: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_per_minute": self.request_per_minute,
            "concurrent_streams": self.concurrent_streams,
            "concurrent_tool_runs": self.concurrent_tool_runs,
            "max_chats": self.max_chats,
            "max_messages_per_chat": self.max_messages_per_chat,
            "max_messages_total": self.max_messages_total,
            "max_artifact_bytes": self.max_artifact_bytes,
            "max_pending_approvals": self.max_pending_approvals,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> QuotaLimits:
        if not d:
            return cls()
        return cls(
            request_per_minute=d.get("request_per_minute"),
            concurrent_streams=d.get("concurrent_streams"),
            concurrent_tool_runs=d.get("concurrent_tool_runs"),
            max_chats=d.get("max_chats"),
            max_messages_per_chat=d.get("max_messages_per_chat"),
            max_messages_total=d.get("max_messages_total"),
            max_artifact_bytes=d.get("max_artifact_bytes"),
            max_pending_approvals=d.get("max_pending_approvals"),
        )


@dataclass
class QuotaUsage:
    """Current usage counters. rate_minute and rate_count for request rate; others are current values."""

    rate_minute: Optional[str] = None  # e.g. "2026-03-04T12:00"
    rate_count: int = 0
    active_streams: int = 0
    active_tool_runs: int = 0
    chat_count: int = 0
    message_count: int = 0
    artifact_bytes: int = 0
    pending_approvals: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rate_minute": self.rate_minute,
            "rate_count": self.rate_count,
            "active_streams": self.active_streams,
            "active_tool_runs": self.active_tool_runs,
            "chat_count": self.chat_count,
            "message_count": self.message_count,
            "artifact_bytes": self.artifact_bytes,
            "pending_approvals": self.pending_approvals,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> QuotaUsage:
        if not d:
            return cls()
        return cls(
            rate_minute=d.get("rate_minute"),
            rate_count=int(d.get("rate_count") or 0),
            active_streams=int(d.get("active_streams") or 0),
            active_tool_runs=int(d.get("active_tool_runs") or 0),
            chat_count=int(d.get("chat_count") or 0),
            message_count=int(d.get("message_count") or 0),
            artifact_bytes=int(d.get("artifact_bytes") or 0),
            pending_approvals=int(d.get("pending_approvals") or 0),
        )


def check_rate(
    limits: QuotaLimits,
    usage: QuotaUsage,
    current_minute: str,
) -> Tuple[bool, str]:
    """Check request rate. usage.rate_minute/rate_count should be updated by caller after allow."""
    if limits.request_per_minute is None:
        return True, "ok"
    if usage.rate_minute != current_minute:
        return True, "ok"  # New minute, count resets
    if usage.rate_count >= limits.request_per_minute:
        return False, "rate_exceeded"
    return True, "ok"


def check_streams(limits: QuotaLimits, usage: QuotaUsage) -> Tuple[bool, str]:
    if limits.concurrent_streams is None:
        return True, "ok"
    if usage.active_streams >= limits.concurrent_streams:
        return False, "streams_exceeded"
    return True, "ok"


def check_tool_runs(limits: QuotaLimits, usage: QuotaUsage) -> Tuple[bool, str]:
    if limits.concurrent_tool_runs is None:
        return True, "ok"
    if usage.active_tool_runs >= limits.concurrent_tool_runs:
        return False, "tool_concurrency_exceeded"
    return True, "ok"


def check_chats(limits: QuotaLimits, usage: QuotaUsage) -> Tuple[bool, str]:
    if limits.max_chats is None:
        return True, "ok"
    if usage.chat_count >= limits.max_chats:
        return False, "chats_exceeded"
    return True, "ok"


def check_messages(
    limits: QuotaLimits,
    usage: QuotaUsage,
    messages_in_chat: Optional[int] = None,
) -> Tuple[bool, str]:
    if limits.max_messages_total is not None and usage.message_count >= limits.max_messages_total:
        return False, "messages_total_exceeded"
    if limits.max_messages_per_chat is not None and messages_in_chat is not None:
        if messages_in_chat >= limits.max_messages_per_chat:
            return False, "messages_per_chat_exceeded"
    return True, "ok"


def check_storage(limits: QuotaLimits, usage: QuotaUsage, additional_bytes: int = 0) -> Tuple[bool, str]:
    if limits.max_artifact_bytes is None:
        return True, "ok"
    if usage.artifact_bytes + additional_bytes > limits.max_artifact_bytes:
        return False, "storage_exceeded"
    return True, "ok"


def check_pending_approvals(limits: QuotaLimits, usage: QuotaUsage) -> Tuple[bool, str]:
    if limits.max_pending_approvals is None:
        return True, "ok"
    if usage.pending_approvals >= limits.max_pending_approvals:
        return False, "pending_approvals_exceeded"
    return True, "ok"
