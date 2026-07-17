from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hg_gateway.approval_notifications import notify_approval_created, notify_social_auto_approved


def test_notify_approval_created_dedupes_by_approval_id():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_gateway.approval_notifications._workspace_root", return_value=root),
            patch("hg_gateway.approval_notifications._notifications_enabled", return_value=True),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            first = notify_approval_created(
                approval_id="apr-1",
                kind="chat_turn",
                title="Approve first reply",
                summary="Reply to the first message",
                risk="low",
                requested_by="gateway",
                chat_id="chat-1",
                assigned_principal_id="principal-1",
            )
            second = notify_approval_created(
                approval_id="apr-1",
                kind="chat_turn",
                title="Approve first reply",
                summary="Reply to the first message",
                risk="low",
                requested_by="gateway",
                chat_id="chat-1",
                assigned_principal_id="principal-1",
            )
        assert first.get("delivery", {}).get("sent") is True
        assert second.get("deduped") is True
        mock_send.assert_called_once()


def test_notify_social_auto_approved_includes_link_and_excerpt():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_gateway.approval_notifications._workspace_root", return_value=root),
            patch("hg_gateway.approval_notifications._notifications_enabled", return_value=True),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify_social_auto_approved(
                approval_id="apr-2",
                task_name="moltbook-engage",
                platform="moltbook",
                mode="reply",
                title="moltbook engage reply",
                content="orbit is not an infinite trash can and we need to stop treating it like one",
                thread_url="https://www.moltbook.com/post/123",
                thread_id="123",
            )
        mock_send.assert_called_once()
        (message,) = mock_send.call_args[0]
        assert "Social post auto-approved" in message
        assert "excerpt:" in message
        assert "https://www.moltbook.com/post/123" in message


def test_notify_social_auto_approved_escapes_markdown_chars():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_gateway.approval_notifications._workspace_root", return_value=root),
            patch("hg_gateway.approval_notifications._notifications_enabled", return_value=True),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify_social_auto_approved(
                approval_id="apr-3",
                task_name="fourclaw-auto-post",
                platform="fourclaw",
                mode="post",
                title="why_everything*breaks[again]",
                content="text with markdown_*_[] characters",
                thread_url="https://example.invalid/thread_[42]",
                thread_id="thread_[42]",
            )
        (message,) = mock_send.call_args[0]
        assert "why\\_everything\\*breaks\\[again\\]" in message
        assert "markdown\\_\\*\\_\\[\\]" in message
        assert "thread\\_\\[42\\]" in message
