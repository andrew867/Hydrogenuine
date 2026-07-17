"""Tests for secret containment and adapter stubs."""

from __future__ import annotations

from hg_runtime.exciton import schema as exciton_schema
from hg_runtime.exciton_action_model import (
    AgentActionType,
    FIXTURE_UTC,
    validate_safe_preview,
)
from hg_runtime.exciton_action_model.adapters import (
    from_exciton_control_request,
    from_social_draft,
    from_social_publish_request,
    from_tool_request,
    from_web_action_request,
    to_operator_queue_item_stub,
)
from hg_runtime.exciton_action_model.validation import _validate_local_ref


def test_no_secret_values_in_sanitized_preview():
    assert validate_safe_preview("Bearer sk-abcdefghijklmnopqrstuvwxyz123456")
    assert not validate_safe_preview("Safe summary only")


def test_safe_preview_passes_clean_text():
    assert not validate_safe_preview("Operator requested status refresh")


def test_raw_payload_ref_local_only():
    assert not _validate_local_ref(".hg-local/social/draft.json")
    assert _validate_local_ref("https://example.com/secret")


def test_adapters_create_non_executing_action_requests():
    draft = from_social_draft(draft_id="d1", surface_id="mastodon", preview="Hello world")
    stub = to_operator_queue_item_stub(draft)
    assert stub["executable"] is False
    assert stub["permission_granted"] is False

    publish = from_social_publish_request(draft_id="d1", surface_id="mastodon", preview="Post")
    assert publish.status.value == "queued"
    assert to_operator_queue_item_stub(publish)["executable"] is False

    web = from_web_action_request(
        action_type=AgentActionType.WEB_READ_URL,
        url="https://example.com/page",
        summary="Read page",
    )
    assert web.raw_payload_ref.startswith(".hg-local/")

    tool = from_tool_request(tool_id="grep", summary="Search files")
    assert tool.action_type == AgentActionType.TOOL_EXECUTE

    ctrl = from_exciton_control_request(
        exciton_schema.ExcitonControlRequest(
            request_id="req-1",
            control=exciton_schema.ExcitonControlKind.PANIC_STOP,
            operator="local-operator",
        )
    )
    assert ctrl.action_type == AgentActionType.PANIC_STOP
    assert ctrl.created_at == FIXTURE_UTC
