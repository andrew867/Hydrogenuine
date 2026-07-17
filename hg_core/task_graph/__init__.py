"""
Task graph (DAG) executor for Hydrogenuine.

Execute predefined DAGs with dependencies, retries, failure propagation,
and dispatch to sub-agents/tools. See docs/specs/dag_executor_contract.md
and .cursor/plans/dag/dag_executor_spec_mvp.md.
"""

from .schema import (
    DAG,
    Node,
    RunPolicy,
    NodePolicy,
    Checkpoints,
    load_dag,
    save_dag,
)
from .validator import validate_dag, ValidationResult
from .validator_diagnostics import Diagnostic, validate_dag_with_diagnostics
from .graph_review import ReviewPolicy, ReviewIssue, annotate_in_loop_body, review_dag
from .planner import DagPlanner, PlannerResult, PlannerConstraints
from .planner_templates import TEMPLATES
from .mermaid import dag_to_mermaid
from .expression import evaluate as evaluate_expression, resolve_var, validate_expression_paths
from .state_machine import NodeStatus, can_transition
from .state_store import RunState, StateStore
from .executor import (
    TaskGraphExecutor,
    topological_order,
    get_ready_nodes,
    resolve_inputs,
)
from . import workflow_registry
from . import fault_injection
from . import retention_redaction_purge
from . import operator_ux
from . import sla_reporting

__all__ = [
    "DAG",
    "Node",
    "RunState",
    "StateStore",
    "RunPolicy",
    "NodePolicy",
    "Checkpoints",
    "load_dag",
    "save_dag",
    "validate_dag",
    "ValidationResult",
    "Diagnostic",
    "validate_dag_with_diagnostics",
    "ReviewPolicy",
    "ReviewIssue",
    "annotate_in_loop_body",
    "review_dag",
    "DagPlanner",
    "PlannerResult",
    "PlannerConstraints",
    "TEMPLATES",
    "dag_to_mermaid",
    "NodeStatus",
    "can_transition",
    "TaskGraphExecutor",
    "topological_order",
    "get_ready_nodes",
    "resolve_inputs",
    "evaluate_expression",
    "resolve_var",
    "validate_expression_paths",
    "workflow_registry",
    "fault_injection",
    "retention_redaction_purge",
    "operator_ux",
    "sla_reporting",
]
