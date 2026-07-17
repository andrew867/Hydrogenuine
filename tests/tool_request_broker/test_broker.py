"""Tool request broker tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import load_registry


def test_approval_receipt_has_scope():
    broker = ToolBroker(load_registry())
    result = broker.submit(new_request(run_id="t1", organ_id="organ:Agent0", capability_id="knowledge_lookup", parameters={"query": "x"}))
    assert result.approval is not None
    assert result.approval.scope
    assert result.approval.expires_at


def test_denial_has_reason():
    broker = ToolBroker(load_registry())
    result = broker.submit(new_request(run_id="t2", organ_id="organ:HRT", capability_id="knowledge_lookup", parameters={"query": "x"}))
    assert result.denial is not None
    assert result.denial.explanation
    assert result.denial.safe_alternative


def test_publish_operator_review():
    broker = ToolBroker(load_registry())
    result = broker.submit(new_request(run_id="t3", organ_id="organ:Agent0", capability_id="social_publish_request", requested_action="publish"))
    assert result.state == "OPERATOR_REVIEW_REQUIRED"
    assert result.denial.operator_required is True
