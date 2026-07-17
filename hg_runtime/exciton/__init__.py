"""EXCITON Phase 0 — operator-facing status/mirror surface for Agent Zero.

EXCITON displays state and proofs and routes requests. It does not authorize, does not
execute, and does not expand autonomy. Every object it emits carries the frozen advisory
constants ``advisory_only=True``, ``permission_granted=False``, ``authority_created=False``.
"""

from hg_runtime.exciton.control_boundary import ExcitonControlBoundary
from hg_runtime.exciton.panel_registry import (
    FORBIDDEN_FIELDS,
    PANEL_CONTRACTS,
    REQUIRED_PANELS,
)
from hg_runtime.exciton.schema import (
    EXCITON_SCHEMA_VERSION,
    ExcitonControlDecision,
    ExcitonControlDecisionKind,
    ExcitonControlKind,
    ExcitonControlRequest,
    ExcitonPanelState,
    ExcitonPanelStatus,
    ExcitonStatusSnapshot,
)
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot

__all__ = [
    "EXCITON_SCHEMA_VERSION",
    "FORBIDDEN_FIELDS",
    "PANEL_CONTRACTS",
    "REQUIRED_PANELS",
    "AggregatorConfig",
    "ExcitonControlBoundary",
    "ExcitonControlDecision",
    "ExcitonControlDecisionKind",
    "ExcitonControlKind",
    "ExcitonControlRequest",
    "ExcitonPanelState",
    "ExcitonPanelStatus",
    "ExcitonStatusSnapshot",
    "build_snapshot",
]
