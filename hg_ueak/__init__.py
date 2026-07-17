"""UEAK — Unified Execution Authority Kernel."""

from __future__ import annotations

import importlib
from typing import Any

from hg_ueak.dispatch import FakeDispatchSink
from hg_ueak.kernel import ExecutionAuthorityKernel
from hg_ueak.models import (
    AuthorityChain,
    EmergencyState,
    ExecutionAdmissionDecision,
    ExecutionCandidate,
    ExecutionDispatchPlan,
    ExecutionReceipt,
    ExecutionRefusalReason,
    ExecutionRequest,
    ExecutionRiskEnvelope,
    ExposureSurface,
    PermitBinding,
    ResourceGovernanceEnvelope,
    RollbackRequirement,
    fixture_execution_request,
)
from hg_ueak.validation import (
    DENIED_CAPABILITY_MISMATCH,
    DENIED_EMERGENCY_RESTRICT,
    DENIED_EXPOSURE_INCREASE,
    DENIED_EXPIRED_PERMIT,
    DENIED_FRESHNESS,
    DENIED_INVALID_PERMIT,
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_IDENTITY,
    DENIED_MISSING_PERMIT,
    DENIED_MISSING_ROLLBACK,
    DENIED_PANIC_LOCKDOWN,
    DENIED_REDACTION_FAILURE,
    DENIED_RESOURCE_BYPASS,
    DENIED_RETENTION_FAILURE,
    DENIED_REVOKED_PERMIT,
    DENIED_STALE_APPROVAL,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CommitScaffold": ("hg_ueak.commit_scaffold", "CommitScaffold"),
    "UEAKStub": ("hg_ueak.stub", "UEAKStub"),
    "ExecutionResult": ("hg_ueak.types", "ExecutionResult"),
    "ScaffoldExecutionRequest": ("hg_ueak.types", "ExecutionRequest"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuthorityChain",
    "CommitScaffold",
    "DENIED_CAPABILITY_MISMATCH",
    "DENIED_EMERGENCY_RESTRICT",
    "DENIED_EXPOSURE_INCREASE",
    "DENIED_EXPIRED_PERMIT",
    "DENIED_FRESHNESS",
    "DENIED_INVALID_PERMIT",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_IDENTITY",
    "DENIED_MISSING_PERMIT",
    "DENIED_MISSING_ROLLBACK",
    "DENIED_PANIC_LOCKDOWN",
    "DENIED_REDACTION_FAILURE",
    "DENIED_RESOURCE_BYPASS",
    "DENIED_RETENTION_FAILURE",
    "DENIED_REVOKED_PERMIT",
    "DENIED_STALE_APPROVAL",
    "EmergencyState",
    "ExecutionAdmissionDecision",
    "ExecutionAuthorityKernel",
    "ExecutionCandidate",
    "ExecutionDispatchPlan",
    "ExecutionReceipt",
    "ExecutionRefusalReason",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionRiskEnvelope",
    "ExposureSurface",
    "FakeDispatchSink",
    "PermitBinding",
    "ResourceGovernanceEnvelope",
    "RollbackRequirement",
    "ScaffoldExecutionRequest",
    "UEAKStub",
    "fixture_execution_request",
]
