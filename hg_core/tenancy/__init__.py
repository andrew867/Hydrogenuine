"""
OS Phase 2: Multi-tenant and environment separation.
tenant_id + environment (dev|staging|prod) isolate ledger, artifacts, and materialized paths.
Pack4: quotas module for tenant resource limits and usage.
"""

from .context import TenantContext, DEFAULT_TENANT_CONTEXT, scope_with_tenancy
from .quotas import (
    QuotaLimits,
    QuotaUsage,
    check_chats,
    check_messages,
    check_pending_approvals,
    check_rate,
    check_storage,
    check_streams,
    check_tool_runs,
)

__all__ = [
    "TenantContext",
    "DEFAULT_TENANT_CONTEXT",
    "scope_with_tenancy",
    "QuotaLimits",
    "QuotaUsage",
    "check_chats",
    "check_messages",
    "check_pending_approvals",
    "check_rate",
    "check_storage",
    "check_streams",
    "check_tool_runs",
]
