"""Tests for DAG tool contract layer: registry, adapter, validator, rate limit, planner."""

import json
import shutil
from pathlib import Path
import uuid
from unittest.mock import patch

import pytest

from hg_core.task_graph.tool_registry import ToolDescriptor, ToolRegistry
from hg_core.task_graph.tool_adapter_contract import ToolResult, ToolError
from hg_core.task_graph.tool_validator import (
    ToolContractError,
    validate_tool_call,
    validate_tool_result,
)
from hg_core.task_graph.rate_limiter import ToolRateLimiter
from hg_core.task_graph.dispatch import (
    make_tool_contract_dispatcher,
    _dispatch_tool_with_contract,
)
from hg_core.task_graph.schema import Node, NodePolicy, Checkpoints


def _minimal_descriptor(
    name: str = "test_tool",
    effect_class: str = "read",
    supports_idempotency_key: bool = False,
    **kwargs,
) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description="test",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        effect_class=effect_class,
        supports_idempotency_key=supports_idempotency_key,
        **kwargs,
    )


# --- Phase 1: Tool registry and descriptors ---


def test_registry_register_get_list():
    """Register a ToolDescriptor; get by name and list return it."""
    reg = ToolRegistry()
    desc = _minimal_descriptor("foo")
    reg.register(desc)
    assert reg.get("foo") is desc
    assert reg.get("foo").name == "foo"
    listed = reg.list()
    assert len(listed) == 1
    assert listed[0] is desc


def test_registry_get_unknown_raises():
    """get(unknown_name) raises KeyError."""
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="Unknown tool"):
        reg.get("nonexistent")


def test_registry_accepts_write_descriptor_with_idempotency():
    """ToolDescriptor with effect_class=write and supports_idempotency_key=True is accepted."""
    reg = ToolRegistry()
    desc = _minimal_descriptor(
        "writer",
        effect_class="write",
        supports_idempotency_key=True,
    )
    reg.register(desc)
    assert reg.get("writer").effect_class == "write"
    assert reg.get("writer").supports_idempotency_key is True


def test_registry_rejects_duplicate_registration():
    reg = ToolRegistry()
    reg.register(_minimal_descriptor("dup_tool"))
    with pytest.raises(ValueError, match="Duplicate tool registration"):
        reg.register(_minimal_descriptor("dup_tool"))


def test_registry_rejects_invalid_effect_class():
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="Invalid effect_class"):
        reg.register(_minimal_descriptor("bad_tool", effect_class="explode"))


def test_registry_describe_all_returns_deterministic_metadata():
    reg = ToolRegistry()
    reg.register(_minimal_descriptor("zeta_tool", effect_class="read", default_timeout_s=20))
    reg.register(_minimal_descriptor("alpha_tool", effect_class="write", supports_idempotency_key=True))
    described = reg.describe_all()
    assert [item["name"] for item in described] == ["alpha_tool", "zeta_tool"]
    assert described[0]["effect_class"] == "write"
    assert described[0]["supports_idempotency_key"] is True


# --- Phase 2: Adapter boundary enforcement ---


def test_validate_tool_call_invalid_input_fails():
    """Invalid input (e.g. not dict) fails before invoke."""
    reg = ToolRegistry()
    reg.register(_minimal_descriptor("foo"))
    with pytest.raises(ToolContractError, match="inputs must be dict"):
        validate_tool_call(
            reg, "foo", "not_a_dict", idempotency_key=None, retries=0, in_loop_body=False
        )


def test_write_tool_requires_idempotency():
    """write tool + retries>0 and idempotency_key None -> ToolContractError."""
    reg = ToolRegistry()
    reg.register(
        _minimal_descriptor("writer", effect_class="write", supports_idempotency_key=True)
    )
    with pytest.raises(ToolContractError, match="idempotency_key"):
        validate_tool_call(
            reg, "writer", {}, idempotency_key=None, retries=1, in_loop_body=False
        )


def test_write_tool_requires_supports_idempotency():
    """write tool + idempotency_key set but supports_idempotency_key False -> ToolContractError."""
    reg = ToolRegistry()
    reg.register(
        _minimal_descriptor("writer", effect_class="write", supports_idempotency_key=False)
    )
    with pytest.raises(ToolContractError, match="does not support idempotency"):
        validate_tool_call(
            reg, "writer", {}, idempotency_key="key", retries=1, in_loop_body=False
        )


def test_validate_tool_result_ok_false_requires_error():
    """ToolResult with ok=False and error None -> validate_tool_result raises."""
    reg = ToolRegistry()
    desc = _minimal_descriptor("foo")
    result = ToolResult(ok=False, outputs={}, error=None)
    with pytest.raises(ToolContractError, match="not ok but no error"):
        validate_tool_result(desc, result, strict=True)


# --- Phase 3: Rate limiting and observability ---


def _minimal_tool_node(tool_name: str = "limited") -> Node:
    return Node(
        id="n1",
        type="tool",
        assigned_entity=tool_name,
        depends_on=[],
        inputs={},
        outputs={},
        policy=NodePolicy(max_retries=0, timeout_s=30),
        checkpoints=Checkpoints(),
    )


def test_rate_limit_excess_invokes_raise():
    """Rate limit: tool with requests_per_minute=2, burst=2; 3rd invoke raises."""
    from hg_core.task_graph.tool_adapter_contract import StubToolAdapter

    reg = ToolRegistry()
    reg.register(
        _minimal_descriptor(
            "limited",
            rate_limit={"requests_per_minute": 2, "burst": 2},
        )
    )
    adapter = StubToolAdapter()
    rate_limiter = ToolRateLimiter()
    node = _minimal_tool_node("limited")
    # First two succeed (burst=2)
    _dispatch_tool_with_contract(
        node, {}, None, reg, adapter, rate_limiter=rate_limiter
    )
    _dispatch_tool_with_contract(
        node, {}, None, reg, adapter, rate_limiter=rate_limiter
    )
    # Third exceeds rate limit
    with pytest.raises(ToolContractError, match="rate limit exceeded"):
        _dispatch_tool_with_contract(
            node, {}, None, reg, adapter, rate_limiter=rate_limiter
        )


def test_tool_invocation_output_includes_usage():
    """ToolResult.usage is present in dispatch output when adapter returns it."""
    from hg_core.task_graph.tool_adapter_contract import ToolAdapter, ToolResult

    class UsageAdapter(ToolAdapter):
        def invoke(self, tool_name, inputs, *, idempotency_key=None, timeout_s=None):
            return ToolResult(
                ok=True,
                outputs={"done": True},
                usage={"external_calls": 1, "tokens": 10},
            )

    reg = ToolRegistry()
    reg.register(_minimal_descriptor("with_usage"))
    adapter = UsageAdapter()
    node = _minimal_tool_node("with_usage")
    out = _dispatch_tool_with_contract(node, {}, None, reg, adapter)
    assert out["ok"] is True
    assert out.get("usage") == {"external_calls": 1, "tokens": 10}


# --- Phase 4: Planner wiring ---


def test_planner_with_registry_only_emits_registered_tool_nodes():
    """Planner with registry containing tools used by template produces valid DAG."""
    from hg_core.task_graph import DagPlanner, PlannerConstraints, validate_dag_with_diagnostics

    reg = ToolRegistry()
    for name in ("state_store", "web_search", "file_writer"):
        reg.register(_minimal_descriptor(name))
    planner = DagPlanner(tool_registry=reg)
    result = planner.plan("Run a weekly job search diff for agent roles")
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True
    tool_entities = [n["assigned_entity"] for n in result.dag["nodes"] if n.get("type") == "tool"]
    assert set(tool_entities) <= {"state_store", "web_search", "file_writer"}


def test_planner_unregistered_tool_returns_error():
    """Planner with registry missing a tool used by template returns UNREGISTERED_TOOL."""
    from hg_core.task_graph import DagPlanner, PlannerConstraints

    reg = ToolRegistry()
    reg.register(_minimal_descriptor("state_store"))
    reg.register(_minimal_descriptor("web_search"))
    # file_writer not registered
    planner = DagPlanner(tool_registry=reg)
    result = planner.plan("Run a weekly job search diff for agent roles")
    assert result.dag is None
    codes = [d.code for d in result.diagnostics]
    assert "UNREGISTERED_TOOL" in codes


def test_planner_tool_node_policy_defaults_from_descriptor():
    """Emitted tool node policy has default_timeout_s and effect_class from descriptor when not overridden."""
    from hg_core.task_graph import DagPlanner

    reg = ToolRegistry()
    reg.register(
        _minimal_descriptor(
            "my_tool",
            default_timeout_s=25,
            effect_class="write",
        )
    )
    # Custom template with one tool node that does not set timeout_s/effect_class
    def custom_template(goal, context, constraints):
        return {
            "graph_id": "custom_with_tool",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {},
            "nodes": [
                {
                    "id": "t1",
                    "type": "tool",
                    "assigned_entity": "my_tool",
                    "depends_on": [],
                    "inputs": {},
                    "outputs": {},
                    "policy": {},
                    "checkpoints": {"before": False, "after": False},
                },
            ],
        }
    planner = DagPlanner(tool_registry=reg, templates={"generic_workflow": custom_template})
    result = planner.plan("Do something arbitrary")
    assert result.dag is not None
    n = result.dag["nodes"][0]
    assert n["policy"].get("timeout_s") == 25
    assert n["policy"].get("effect_class") == "write"


def test_native_adapter_records_idempotency_ledger_and_reuses_result():
    from hg_core.task_graph.tool_adapter import NativeTaskToolAdapter

    call_counter = {"count": 0}

    def _fake_run_task_tool(tool_name, inputs, timeout_s=300):
        call_counter["count"] += 1
        return {"ok": True, "outputs": {"reply": "done"}, "external_calls": 1}

    tmp = Path("temp") / f"tool_adapter_phase2_{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        with (
            patch("hg_core.task_graph.tool_adapter.get_workspace_root", return_value=tmp),
            patch("hg_core.task_graph.tool_adapter.get_session_target", return_value="automation-test-tool"),
            patch("hg_core.task_graph.tool_adapter.run_task_tool", side_effect=_fake_run_task_tool),
        ):
            adapter = NativeTaskToolAdapter()
            first = adapter.invoke("test-tool", {"goal": "ship"}, idempotency_key="idem-1", timeout_s=120)
            second = adapter.invoke("test-tool", {"goal": "ship"}, idempotency_key="idem-1", timeout_s=120)

        assert first.ok is True
        assert second.ok is True
        assert call_counter["count"] == 1
        assert second.metadata is not None
        assert second.metadata.get("dedupe_hit") is True
        ledger = tmp / "memory" / "automation" / "automation-test-tool" / "post_dedupe.json"
        assert ledger.exists()
        payload = json.loads(ledger.read_text(encoding="utf-8"))
        assert "entries" in payload
        assert "idem-1" in payload["entries"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
