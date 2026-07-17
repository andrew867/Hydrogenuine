"""Engage reply quality helpers in social_outbound."""

from hg_core.task_graph.social_outbound import (
    is_engage_decline_to_reply,
    is_engage_template_bloat,
    resolve_engage_reply_action,
    validate_outbound_social_text,
)


def test_engage_decline_detects_stays_quiet_meta():
    text = (
        "look, ZoClxud's already nailed it — the thread is doing the work. "
        "this run stays quiet. better work is watching what happens next than adding noise to a thread that's already hot and pointed."
    )
    declined, reason = is_engage_decline_to_reply(text)
    assert declined
    assert reason in {"this run stays quiet", "better work is watching", "adding noise to a thread", "already hot and pointed"}


def test_resolve_engage_reply_no_reply_prefix():
    action, reason, publish_text = resolve_engage_reply_action("NO_REPLY: thread already covered")
    assert action == "decline"
    assert "thread already covered" in reason
    assert publish_text == ""


def test_validate_reply_blocks_decline_meta():
    text = "this run stays quiet. nothing to add."
    ok, block_reason = validate_outbound_social_text("fourclaw", text, kind="reply")
    assert not ok
    assert block_reason.startswith("engage_declined:")


def test_engage_template_bloat_detects_op_cut_off_meta():
    text = "I'm reading this thread and the OP got cut off mid-sentence before I punch out a reply."
    flagged, reason = is_engage_template_bloat(text)
    assert flagged
    assert reason in {"i'm reading this thread", "op got cut off", "got cut off mid-sentence"}


def test_engage_template_bloat_allows_direct_reply():
    text = "The bottleneck is your queue depth, not the model latency. Ship a backpressure limit first."
    flagged, _ = is_engage_template_bloat(text)
    assert not flagged
