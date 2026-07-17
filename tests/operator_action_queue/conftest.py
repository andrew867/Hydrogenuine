"""Operator action queue test fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.adapters import _base_request
from hg_runtime.exciton_action_model.schema import AgentActionRequest
from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime
from hg_runtime.operator_action_queue.store import OperatorQueueStore


def make_store(tmp_path: Path) -> OperatorQueueStore:
    root = tmp_path / "queue"
    root.mkdir(parents=True, exist_ok=True)
    return OperatorQueueStore(root / "operator_action_queue.json", root / "operator_action_receipts.jsonl")


def make_runtime(tmp_path: Path) -> OperatorQueueRuntime:
    return OperatorQueueRuntime(make_store(tmp_path))


def sample_request(
    action_type: AgentActionType = AgentActionType.STATUS_REFRESH,
    **kwargs,
) -> AgentActionRequest:
    return _base_request(action_type, **kwargs)
