"""IAM operator authority types — local registry mode (CT-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AGENT_ZERO_ID = "agent:0"

AUTHORITY_SCOPES = frozenset(
    {
        "approve_change",
        "approve_high_risk",
        "emergency_override",
        "panic",
        "configure",
        "audit_read",
    }
)


@dataclass(frozen=True)
class OperatorRecord:
    operator_id: str
    display_name: str
    authority_scopes: tuple[str, ...]
    key_ref: str
    status: str  # active | revoked

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "display_name": self.display_name,
            "authority_scopes": list(self.authority_scopes),
            "key_ref": self.key_ref,
            "status": self.status,
        }


@dataclass(frozen=True)
class OperatorRegistry:
    schema: str
    schema_version: str
    mode: str
    tenant_id: str
    operators: tuple[OperatorRecord, ...]
    legacy_aliases: dict[str, str]
    registry_hash: str
    source_path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "mode": self.mode,
            "tenant_id": self.tenant_id,
            "operators": [op.to_payload() for op in self.operators],
            "legacy_aliases": dict(sorted(self.legacy_aliases.items())),
            "registry_hash": self.registry_hash,
        }


@dataclass(frozen=True)
class AuthorityBinding:
    """Binds a registered operator to a scope and registry anchor."""

    operator_id: str
    session_id: str
    registry_hash: str
    scope: str
    tenant_id: str = "default"

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "session_id": self.session_id,
            "registry_hash": self.registry_hash,
            "scope": self.scope,
            "tenant_id": self.tenant_id,
        }


@dataclass(frozen=True)
class AuthorityResult:
    ok: bool
    reason_code: str
    binding: AuthorityBinding | None = None
    resolved_operator_id: str | None = None


@dataclass
class IamEventLedger:
    """In-process IAM admission events for receipts and gate evidence."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        actor: str,
        scope: str,
        session_id: str,
        ok: bool,
        reason_code: str,
        checkpoint: str,
        binding: AuthorityBinding | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "actor": actor,
            "scope": scope,
            "session_id": session_id,
            "ok": ok,
            "reason_code": reason_code,
            "checkpoint": checkpoint,
        }
        if binding is not None:
            entry["binding"] = binding.to_payload()
        self.events.append(entry)

    def clear(self) -> None:
        self.events.clear()


_GLOBAL_LEDGER = IamEventLedger()


def iam_event_ledger() -> IamEventLedger:
    return _GLOBAL_LEDGER


def reset_iam_event_ledger() -> None:
    _GLOBAL_LEDGER.clear()


__all__ = [
    "AGENT_ZERO_ID",
    "AUTHORITY_SCOPES",
    "AuthorityBinding",
    "AuthorityResult",
    "IamEventLedger",
    "OperatorRecord",
    "OperatorRegistry",
    "iam_event_ledger",
    "reset_iam_event_ledger",
]
