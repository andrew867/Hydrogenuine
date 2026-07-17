"""Swarm contracts: SwarmPlan (max_children, budgets), SwarmResult (child_run_ids, outputs, status)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hg_quantum.entanglement.contracts import SymmetryConfig
    from hg_quantum.error_correction.contracts import VerificationGraph

# Hard cap for backpressure (Phase 5)
MAX_SWARM_CHILDREN = 100


@dataclass(frozen=True)
class SwarmPlan:
    """Plan for a swarm run: list of child tasks, caps and per-child budgets."""
    summary: str
    tasks: List[Dict[str, Any]]  # each: workflow_id, inputs (optional: run_config, timeout_s)
    max_children: int = 10
    max_tool_calls_per_child: int = 50
    max_wall_clock_s_per_child: int = 300
    max_wall_clock_s: Optional[float] = None  # total wall clock for entire swarm
    correlation_id: str = ""
    tenant_id: str = "default"
    actor_id: str = "swarm"


@dataclass(frozen=True)
class QuantumSwarmPlan(SwarmPlan):
    """Extended swarm plan with quantum cognitive engine options."""

    fingerprint_id: str = ""
    base_fingerprint: Optional[Dict[str, Any]] = None
    task_profile: Optional[Dict[str, Any]] = None
    symmetry_config: Optional["SymmetryConfig"] = None
    verification_graph: Optional["VerificationGraph"] = None
    risk_skew: Optional[Dict[str, Any]] = None
    force_quantum: bool = False


@dataclass
class SwarmResult:
    """Result of a swarm run: child run ids, outputs, status and counts."""
    swarm_run_id: str
    correlation_id: str
    child_run_ids: List[str]
    child_outputs: List[Dict[str, Any]]
    child_statuses: List[str]  # "completed" | "failed"
    status: str  # "completed" | "partial" | "failed"
    counts: Dict[str, int]  # launched, completed, failed
    summary: str
    artifacts: Dict[str, Any]
    warnings: List[str]
    artifacts_path: Optional[str] = None
