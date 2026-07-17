"""Organ tool access tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.organ_access import organ_may_request, load_organ_allowlists
from hg_runtime.tool_capability_fabric.registry import load_registry


def test_agent0_may_knowledge():
    assert organ_may_request("organ:Agent0", "knowledge_lookup")


def test_hrt_denied_out_of_scope():
    broker = ToolBroker(load_registry())
    result = broker.submit(new_request(run_id="o1", organ_id="organ:HRT", capability_id="knowledge_lookup", parameters={"query": "x"}))
    assert result.state == "DENIED"
    assert result.denial.denial_reason == "ORGAN_SCOPE_DENIED"


def test_allowlists_loaded():
    lists = load_organ_allowlists()
    assert "organ:Agent0" in lists
