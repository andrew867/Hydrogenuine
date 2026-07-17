"""
Tenant and environment context: tenant_id, environment (dev|staging|prod).
Use scope_with_tenancy() to build a scope dict for ledger emit that includes tenant_id and environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    environment: str  # dev | staging | prod


DEFAULT_TENANT_CONTEXT = TenantContext(tenant_id="default", environment="prod")


def scope_with_tenancy(
    scope_type: str,
    scope_id: str,
    tenant_id: str = "default",
    environment: str = "prod",
) -> Dict[str, Any]:
    """Build a scope dict including tenant_id and environment for ledger path isolation."""
    if environment not in ("dev", "staging", "prod"):
        raise ValueError("environment must be dev, staging, or prod")
    return {
        "type": scope_type,
        "id": scope_id,
        "tenant_id": tenant_id,
        "environment": environment,
    }
