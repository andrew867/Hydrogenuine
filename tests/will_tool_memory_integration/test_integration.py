"""WILL tool and memory integration tests."""

from hg_runtime.tool_capability_fabric.broker import ToolBroker
from hg_runtime.tool_capability_fabric.registry import load_registry
from hg_runtime.will_module.agent0 import build_agent0_will_context
from hg_runtime.will_module.memory_context import memory_write_intent_to_request
from hg_runtime.will_module.schema import MemoryWriteIntent, SocialPublicationIntent, ToolRequestIntent
from hg_runtime.will_module.tool_context import social_intent_to_request, submit_with_will_context, tool_intent_to_request


def test_social_intent_becomes_publish_request_not_execution():
    will = build_agent0_will_context(run_id="run-soc", will_profile="configs/will/agent0_dev_boot_will.example.json")
    intent = SocialPublicationIntent(channel="local", purpose="test draft path")
    ctx = social_intent_to_request(intent, run_id="run-soc", will_context=will.will_context)
    broker = ToolBroker(load_registry())
    result = submit_with_will_context(broker, ctx, execute_local=True)
    assert result.state in {"OPERATOR_REVIEW_REQUIRED", "DENIED"}
    assert result.execution is None or result.execution.live_side_effect is False


def test_memory_write_intent_no_mutation():
    will = build_agent0_will_context(run_id="run-mem", will_profile="configs/will/agent0_dev_boot_will.example.json")
    intent = MemoryWriteIntent(region="session", purpose="note intent")
    req = memory_write_intent_to_request(intent, will.will_context)
    payload = req.to_payload()
    assert payload["write_performed"] is False
    assert payload["will_approved_write"] is False


def test_tool_intent_contextualizes_only():
    will = build_agent0_will_context(run_id="run-tool", will_profile="configs/will/agent0_dev_boot_will.example.json")
    intent = ToolRequestIntent(tool_class="knowledge_lookup", purpose="doctrine check")
    ctx = tool_intent_to_request(intent, run_id="run-tool", capability_id="knowledge_lookup", will_context=will.will_context)
    assert ctx.will_explanation
    assert ctx.to_payload()["will_approved_request"] is False


def test_browser_live_intent_still_governed():
    will = build_agent0_will_context(run_id="run-br", will_profile="configs/will/agent0_dev_boot_will.example.json")
    intent = ToolRequestIntent(tool_class="browser_open_url_request", purpose="read example")
    ctx = tool_intent_to_request(
        intent, run_id="run-br", capability_id="browser_open_url_request", will_context=will.will_context
    )
    broker = ToolBroker(load_registry())
    result = submit_with_will_context(broker, ctx)
    assert result.state in {"DENIED", "APPROVED_SCOPED", "EXECUTED", "OPERATOR_REVIEW_REQUIRED"}


def test_research_hypothesis_not_proven():
    from hg_runtime.will_module.research_hypotheses import load_research_hypothesis, validate_hypothesis_bounded

    hyp = load_research_hypothesis("configs/will/research_hypotheses/microtubule_thz_will_hypothesis.example.json")
    failures = validate_hypothesis_bounded(hyp)
    assert failures == []
    for claim in hyp.claims:
        assert claim.proven is False
