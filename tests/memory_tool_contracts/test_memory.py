"""Memory tool contract tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import load_registry
from hg_runtime.tool_capability_fabric.tools import memory_read_tool, memory_write_request_tool


def test_memory_read_advisory():
    result = memory_read_tool()
    assert result["is_proof"] is False
    assert result["is_truth"] is False


def test_memory_write_request_no_mutation():
    req = memory_write_request_tool(content="note", key="k1")
    assert req["write_performed"] is False
    broker = ToolBroker(load_registry())
    r = broker.submit(new_request(run_id="m1", organ_id="organ:Agent0", capability_id="memory_write_request", requested_action="write", parameters={"content": "x"}))
    assert r.state == "OPERATOR_REVIEW_REQUIRED"
    assert r.denial is not None
    assert r.execution is None or r.execution.live_side_effect is False
