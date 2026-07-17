"""Email social account contract tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import load_registry
from hg_runtime.tool_capability_fabric.tools import email_draft_tool


def test_email_draft_no_send():
    d = email_draft_tool(to="a@b.com", subject="s", body="b")
    assert d["result"]["sent"] is False


def test_publish_operator_review():
    b = ToolBroker(load_registry())
    r = b.submit(new_request(run_id="t", organ_id="organ:Agent0", capability_id="social_publish_request", requested_action="publish"))
    assert r.state == "OPERATOR_REVIEW_REQUIRED"
