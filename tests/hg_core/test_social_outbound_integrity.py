"""Validator extensions R7/R8 for social outbound integrity."""

from hg_core.task_graph.social_outbound import (
    is_meta_navel_gaze,
    is_structured_decision_leakage,
    validate_outbound_social_text,
)


def test_r7_blocks_json_research_body():
    body = '{"action": "research", "reason": "need more signal"}'
    flagged, reason = is_structured_decision_leakage("", body)
    assert flagged
    assert reason.startswith("structured_decision_leak")
    ok, block_reason = validate_outbound_social_text("moltbook", body, kind="post")
    assert not ok
    assert "structured_decision" in block_reason


def test_r7_blocks_json_fence_title():
    flagged, reason = is_structured_decision_leakage("```json", "some body")
    assert flagged
    assert "title_fence" in reason


def test_r8_blocks_meta_navel_entity_counts():
    body = "244 posts. 220 automation entities in the fleet summary."
    flagged, reason = is_meta_navel_gaze(body)
    assert flagged
    assert reason == "meta_navel_gaze"
    ok, block_reason = validate_outbound_social_text("moltbook", body, kind="post", title="stats")
    assert not ok
    assert "meta_navel" in block_reason


def test_r7_r8_allow_valid_news_post():
    title = "Banks are mispricing duration again"
    body = "When funding costs jump, the first failure mode is liquidity hoarding, not credit losses."
    ok, reason = validate_outbound_social_text("moltbook", body, kind="post", title=title)
    assert ok, reason
