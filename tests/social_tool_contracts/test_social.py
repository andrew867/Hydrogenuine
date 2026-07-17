"""Social tool contract tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import load_registry
from hg_runtime.tool_capability_fabric.tools import social_draft_tool


def test_social_draft_not_publication():
    draft = social_draft_tool(text="hello")
    assert draft["is_publication"] is False
    assert draft["result"]["published"] is False


def test_publish_request_review():
    broker = ToolBroker(load_registry())
    r = broker.submit(new_request(run_id="s1", organ_id="organ:Agent0", capability_id="social_publish_request", requested_action="publish"))
    assert r.state == "OPERATOR_REVIEW_REQUIRED"
