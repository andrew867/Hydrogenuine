"""
DAG and node schema for task graph execution.

Defines data structures for graph-level config and per-node config.
Runtime-only fields (status, attempt_count, timestamps, error, trace_ref)
are optional in the schema and set by the executor.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# Node types allowed in the DAG
NODE_TYPES = ("agent", "tool", "transform", "eval", "gate", "loop")

# Effect class for side-effect policy: none (pure), read (external reads), write (external writes)
EFFECT_CLASSES = ("none", "read", "write")

# Loop on_body_failure: stop_loop (default), fail_run, continue_iteration (future)
LOOP_ON_BODY_FAILURE = ("stop_loop", "fail_run", "continue_iteration")

# Failure modes at graph level
FAILURE_MODES = ("fail_fast", "continue")

# Input binding modes: strict = fail node on unresolved refs; blocked = set status BLOCKED; lenient = pass through
INPUT_BINDING_MODES = ("strict", "lenient", "blocked")


@dataclass
class RunPolicy:
    """Graph-level run policy."""
    max_concurrency: int = 1
    failure_mode: str = "fail_fast"
    strict_bindings: bool = True  # when true, validation fails on invalid $node.<id>.<key> refs
    input_binding_mode: str = "strict"  # strict | lenient | blocked
    allow_side_effects_in_loops: bool = False
    expression_strict_mode: bool = False
    max_node_executions: Optional[int] = None
    max_total_runtime_s: Optional[int] = None
    default_retry_backoff_ms: Optional[int] = None
    max_state_bytes: Optional[int] = None
    max_state_keys: Optional[int] = None
    loop_policy_on_body_failure: str = "stop_loop"  # stop_loop | fail_run | continue_iteration
    pause_at_checkpoint: bool = False  # HITL: pause at any checkpoint (before/after) and return paused
    budgets: Optional[Dict[str, Any]] = None  # effect budgets: name -> { limit, hard, scope, on_exceed }

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"max_concurrency": self.max_concurrency, "failure_mode": self.failure_mode}
        if self.strict_bindings is not True:
            out["strict_bindings"] = self.strict_bindings
        if self.input_binding_mode != "strict":
            out["input_binding_mode"] = self.input_binding_mode
        if self.allow_side_effects_in_loops:
            out["allow_side_effects_in_loops"] = self.allow_side_effects_in_loops
        if self.expression_strict_mode:
            out["expression_strict_mode"] = self.expression_strict_mode
        if self.max_node_executions is not None:
            out["max_node_executions"] = self.max_node_executions
        if self.max_total_runtime_s is not None:
            out["max_total_runtime_s"] = self.max_total_runtime_s
        if self.default_retry_backoff_ms is not None:
            out["default_retry_backoff_ms"] = self.default_retry_backoff_ms
        if self.max_state_bytes is not None:
            out["max_state_bytes"] = self.max_state_bytes
        if self.max_state_keys is not None:
            out["max_state_keys"] = self.max_state_keys
        if self.loop_policy_on_body_failure != "stop_loop":
            out["loop_policy_on_body_failure"] = self.loop_policy_on_body_failure
        if self.pause_at_checkpoint:
            out["pause_at_checkpoint"] = self.pause_at_checkpoint
        if self.budgets is not None:
            out["budgets"] = dict(self.budgets)
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RunPolicy:
        return cls(
            max_concurrency=d.get("max_concurrency", 1),
            failure_mode=d.get("failure_mode", "fail_fast"),
            strict_bindings=d.get("strict_bindings", True),
            input_binding_mode=d.get("input_binding_mode", "strict"),
            allow_side_effects_in_loops=d.get("allow_side_effects_in_loops", False),
            expression_strict_mode=d.get("expression_strict_mode", False),
            max_node_executions=d.get("max_node_executions"),
            max_total_runtime_s=d.get("max_total_runtime_s"),
            default_retry_backoff_ms=d.get("default_retry_backoff_ms"),
            max_state_bytes=d.get("max_state_bytes"),
            max_state_keys=d.get("max_state_keys"),
            loop_policy_on_body_failure=d.get("loop_policy_on_body_failure", "stop_loop"),
            pause_at_checkpoint=d.get("pause_at_checkpoint", False),
            budgets=d.get("budgets"),
        )


@dataclass
class NodePolicy:
    """Per-node execution policy."""
    timeout_s: Optional[int] = None
    max_retries: int = 0
    retry_backoff_ms: int = 500
    escalation: Optional[str] = None
    budget_tokens: Optional[int] = None
    memory_profile: Optional[str] = None  # none | light_context | full_context | entity_recall
    max_iterations: Optional[int] = None  # required and >= 1 for type=loop
    idempotency_key: Optional[str] = None  # expression for write nodes in loops/retries
    effect_class: str = "none"  # none | read | write
    side_effect: Optional[bool] = None  # backward compat: true -> write, false -> none

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if self.timeout_s is not None:
            out["timeout_s"] = self.timeout_s
        out["max_retries"] = self.max_retries
        out["retry_backoff_ms"] = self.retry_backoff_ms
        if self.escalation is not None:
            out["escalation"] = self.escalation
        if self.budget_tokens is not None:
            out["budget_tokens"] = self.budget_tokens
        if self.memory_profile is not None:
            out["memory_profile"] = self.memory_profile
        if self.max_iterations is not None:
            out["max_iterations"] = self.max_iterations
        if self.idempotency_key is not None:
            out["idempotency_key"] = self.idempotency_key
        if self.effect_class != "none":
            out["effect_class"] = self.effect_class
        if self.side_effect is not None:
            out["side_effect"] = self.side_effect
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NodePolicy:
        effect = d.get("effect_class")
        side_effect = d.get("side_effect")
        if effect is None and side_effect is not None:
            effect = "write" if side_effect else "none"
        elif effect is None:
            effect = "none"
        return cls(
            timeout_s=d.get("timeout_s"),
            max_retries=d.get("max_retries", 0),
            retry_backoff_ms=d.get("retry_backoff_ms", 500),
            escalation=d.get("escalation"),
            budget_tokens=d.get("budget_tokens"),
            memory_profile=d.get("memory_profile"),
            max_iterations=d.get("max_iterations"),
            idempotency_key=d.get("idempotency_key"),
            effect_class=effect,
            side_effect=side_effect,
        )


@dataclass
class Checkpoints:
    """Overseer checkpoint flags for a node. pause_before/pause_after enable HITL pause at this node."""
    before: bool = False
    after: bool = False
    pause_before: bool = False
    pause_after: bool = False

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"before": self.before, "after": self.after}
        if self.pause_before:
            out["pause_before"] = self.pause_before
        if self.pause_after:
            out["pause_after"] = self.pause_after
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Checkpoints:
        return cls(
            before=d.get("before", False),
            after=d.get("after", False),
            pause_before=d.get("pause_before", False),
            pause_after=d.get("pause_after", False),
        )


@dataclass
class Node:
    """
    Single node in the DAG.

    Required: id, type, assigned_entity, depends_on, inputs, outputs, policy, checkpoints.
    Runtime-only (set by executor): status, attempt_count, started_at, ended_at, error, trace_ref.
    """
    id: str
    type: str  # agent | tool | transform | eval | gate | loop
    assigned_entity: str
    depends_on: List[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    policy: NodePolicy
    checkpoints: Checkpoints
    # Runtime-only (optional in JSON; executor sets these)
    status: Optional[str] = None
    attempt_count: int = 0
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    trace_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "assigned_entity": self.assigned_entity,
            "depends_on": list(self.depends_on),
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "policy": self.policy.to_dict(),
            "checkpoints": self.checkpoints.to_dict(),
        }
        if self.status is not None:
            d["status"] = self.status
        if self.attempt_count != 0:
            d["attempt_count"] = self.attempt_count
        if self.started_at is not None:
            d["started_at"] = self.started_at
        if self.ended_at is not None:
            d["ended_at"] = self.ended_at
        if self.error is not None:
            d["error"] = self.error
        if self.trace_ref is not None:
            d["trace_ref"] = self.trace_ref
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Node:
        return cls(
            id=d["id"],
            type=d["type"],
            assigned_entity=d["assigned_entity"],
            depends_on=list(d.get("depends_on", [])),
            inputs=dict(d.get("inputs", {})),
            outputs=dict(d.get("outputs", {})),
            policy=NodePolicy.from_dict(d.get("policy", {})),
            checkpoints=Checkpoints.from_dict(d.get("checkpoints", {})),
            status=d.get("status"),
            attempt_count=d.get("attempt_count", 0),
            started_at=d.get("started_at"),
            ended_at=d.get("ended_at"),
            error=d.get("error"),
            trace_ref=d.get("trace_ref"),
        )


@dataclass
class DAG:
    """
    Top-level DAG definition.

    graph_id, version, run_policy, inputs, nodes.
    """
    graph_id: str
    version: str
    run_policy: RunPolicy
    inputs: Dict[str, Any]
    nodes: List[Node]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "version": self.version,
            "run_policy": self.run_policy.to_dict(),
            "inputs": dict(self.inputs),
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DAG:
        return cls(
            graph_id=d["graph_id"],
            version=d.get("version", "1.0"),
            run_policy=RunPolicy.from_dict(d.get("run_policy", {})),
            inputs=dict(d.get("inputs", {})),
            nodes=[Node.from_dict(n) for n in d.get("nodes", [])],
        )


def load_dag(path: Path) -> DAG:
    """Load a DAG from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return DAG.from_dict(data)


def save_dag(dag: DAG, path: Path) -> None:
    """Save a DAG to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dag.to_dict(), f, indent=2)
