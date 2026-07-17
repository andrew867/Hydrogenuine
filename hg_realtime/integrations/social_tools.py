"""
Social tool pack: fourclaw and moltbook tools implemented via hg_platforms.

All tools are gated by real API config: when real external APIs are disabled
(default), read tools return a safe empty shape; write tools return
ok=False, error="real_apis_disabled". When enabled, tools call hg_platforms
clients (fourclaw_api_client, moltbook_api_client).
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from .tool_router import ToolCall

# Config: enable real external API calls for social platforms.
# Set HG_REALTIME_REAL_SOCIAL_APIS=1 (and provide FOURCLAW_API_KEY / moltbook creds) for E2E.
def _real_social_apis_enabled() -> bool:
    import os
    return os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS", "").strip() in ("1", "true", "yes")


def _get(call: ToolCall, key: str, default: Any = None) -> Any:
    return call.args.get(key, default)


# --- Fourclaw ---

def _handler_fourclaw_getposts(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or _get(call, "board_slug") or "/b"
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    limit = _get(call, "limit")
    if limit is None:
        limit = 20
    limit = min(int(limit), 20) if limit is not None else 20
    include_media = bool(_get(call, "include_media", False))
    include_content = bool(_get(call, "include_content", False))

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"threads": []}, "action": "list_threads"}

    try:
        from hg_platforms.fourclaw.fourclaw_api_client import list_threads
        result = list_threads(
            board_slug=board,
            limit=limit,
            include_media=include_media,
            include_content=include_content,
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "list_threads"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "list_threads"}
    return {"ok": True, "data": result, "action": "list_threads"}


def _handler_fourclaw_get_thread(call: ToolCall) -> Dict[str, Any]:
    thread_id = _get(call, "thread_id")
    if not thread_id:
        return {"ok": False, "error": "thread_id is required", "action": "get_thread"}

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"id": str(thread_id), "replies": []}, "action": "get_thread"}

    try:
        from hg_platforms.fourclaw.fourclaw_api_client import get_thread
        result = get_thread(thread_id=str(thread_id))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_thread"}
    return {"ok": True, "data": result, "action": "get_thread"}


def _handler_fourclaw_create_thread(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or _get(call, "board_slug")
    title = _get(call, "title")
    content = _get(call, "content")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not board or not title:
        return {"ok": False, "error": "board and title are required", "action": "create_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "create_thread"}

    try:
        from hg_platforms.fourclaw.fourclaw_api_client import create_thread
        result = create_thread(
            board_slug=board,
            title=str(title),
            content=str(content) if content else None,
            anon=bool(_get(call, "anon", False)),
            media=_get(call, "media"),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "create_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "create_thread"}
    return {"ok": True, "data": result, "action": "create_thread"}


def _handler_fourclaw_reply(call: ToolCall) -> Dict[str, Any]:
    thread_id = _get(call, "thread_id")
    content = _get(call, "content")
    if not thread_id or not content:
        return {"ok": False, "error": "thread_id and content are required", "action": "reply_to_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "reply_to_thread"}

    try:
        from hg_platforms.fourclaw.fourclaw_api_client import reply_to_thread
        result = reply_to_thread(
            thread_id=str(thread_id),
            content=str(content),
            anon=bool(_get(call, "anon", False)),
            bump=bool(_get(call, "bump", True)),
            media=_get(call, "media"),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "reply_to_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "reply_to_thread"}
    return {"ok": True, "data": result, "action": "reply_to_thread"}


# --- Aichan (aichan.lol / "lolchan") ---

def _handler_aichan_getposts(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"threads": []}, "action": "list_threads"}

    try:
        from aichan.aichan_api_client import list_threads
        result = list_threads(str(board))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "list_threads"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "list_threads"}
    return {"ok": True, "data": result, "action": "list_threads"}


def _handler_aichan_get_thread(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    thread_id = _get(call, "thread_id")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not thread_id:
        return {"ok": False, "error": "thread_id is required", "action": "get_thread"}

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"thread_id": str(thread_id), "posts": []}, "action": "get_thread"}

    try:
        from aichan.aichan_api_client import get_thread
        result = get_thread(str(board), str(thread_id))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_thread"}
    return {"ok": True, "data": result, "action": "get_thread"}


def _handler_aichan_create_thread(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    subject = _get(call, "subject") or _get(call, "title")
    content = _get(call, "content") or _get(call, "body")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not subject or not content:
        return {"ok": False, "error": "board, subject/title, and content/body are required", "action": "create_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "create_thread"}

    try:
        from aichan.aichan_api_client import create_thread
        result = create_thread(
            board=str(board),
            subject=str(subject),
            body=str(content),
            name=str(_get(call, "name") or ""),
            email=str(_get(call, "email") or ""),
            password=str(_get(call, "password") or ""),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "create_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "create_thread"}
    return {"ok": True, "data": result, "action": "create_thread"}


def _handler_aichan_reply(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    thread_id = _get(call, "thread_id")
    content = _get(call, "content") or _get(call, "body")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not thread_id or not content:
        return {"ok": False, "error": "thread_id and content/body are required", "action": "reply_to_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "reply_to_thread"}

    try:
        from aichan.aichan_api_client import reply_to_thread
        result = reply_to_thread(
            board=str(board),
            thread_id=str(thread_id),
            body=str(content),
            name=str(_get(call, "name") or ""),
            email=str(_get(call, "email") or "sage"),
            password=str(_get(call, "password") or ""),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "reply_to_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "reply_to_thread"}
    return {"ok": True, "data": result, "action": "reply_to_thread"}


# --- Agentchan ---

def _handler_agentchan_getposts(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    limit = _get(call, "limit", 10)
    limit = min(int(limit), 50) if limit is not None else 10

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"threads": []}, "action": "list_threads"}

    try:
        import asyncio
        from agentchan.agentchan_api_client_async import AgentchanAsyncClient

        async def _run() -> Dict[str, Any]:
            async with AgentchanAsyncClient(task_name=_get(call, "task_name")) as client:
                return await client.list_threads(str(board), limit=limit)

        result = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "list_threads"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "list_threads"}
    return {"ok": True, "data": result, "action": "list_threads"}


def _handler_agentchan_get_thread(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    thread_id = _get(call, "thread_id")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not thread_id:
        return {"ok": False, "error": "thread_id is required", "action": "get_thread"}

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"thread": {"id": str(thread_id)}, "posts": []}, "action": "get_thread"}

    try:
        import asyncio
        from agentchan.agentchan_api_client_async import AgentchanAsyncClient

        async def _run() -> Dict[str, Any]:
            async with AgentchanAsyncClient(task_name=_get(call, "task_name")) as client:
                return await client.get_thread(str(board), str(thread_id))

        result = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_thread"}
    return {"ok": True, "data": result, "action": "get_thread"}


def _handler_agentchan_get_replies(call: ToolCall) -> Dict[str, Any]:
    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"replies": []}, "action": "get_agent_replies"}

    try:
        import asyncio
        from agentchan.agentchan_api_client_async import AgentchanAsyncClient

        async def _run() -> Dict[str, Any]:
            async with AgentchanAsyncClient(task_name=_get(call, "task_name")) as client:
                since = _get(call, "since")
                return await client.get_agent_replies(since=int(since)) if since else await client.get_agent_replies()

        result = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_agent_replies"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_agent_replies"}
    return {"ok": True, "data": result, "action": "get_agent_replies"}


def _handler_agentchan_create_thread(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    subject = _get(call, "subject") or _get(call, "title")
    content = _get(call, "content")
    challenge_id = _get(call, "challenge_id")
    result_hash = _get(call, "result_hash")
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not board or not subject or not content or not challenge_id or not result_hash:
        return {"ok": False, "error": "board, subject/title, content, challenge_id, and result_hash are required", "action": "create_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "create_thread"}

    try:
        import asyncio
        from agentchan.agentchan_api_client_async import AgentchanAsyncClient

        async def _run() -> Dict[str, Any]:
            async with AgentchanAsyncClient(task_name=_get(call, "task_name")) as client:
                return await client.create_thread(str(board), str(subject), str(content), str(challenge_id), str(result_hash))

        result = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "create_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "create_thread"}
    return {"ok": True, "data": result, "action": "create_thread"}


def _handler_agentchan_reply(call: ToolCall) -> Dict[str, Any]:
    board = _get(call, "board") or "b"
    thread_id = _get(call, "thread_id")
    content = _get(call, "content")
    challenge_id = _get(call, "challenge_id")
    result_hash = _get(call, "result_hash")
    sage = bool(_get(call, "sage", False))
    if isinstance(board, str) and board.startswith("/"):
        board = board.lstrip("/") or "b"
    if not board or not thread_id or not content or not challenge_id or not result_hash:
        return {"ok": False, "error": "board, thread_id, content, challenge_id, and result_hash are required", "action": "reply_to_thread"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "reply_to_thread"}

    try:
        import asyncio
        from agentchan.agentchan_api_client_async import AgentchanAsyncClient

        async def _run() -> Dict[str, Any]:
            async with AgentchanAsyncClient(task_name=_get(call, "task_name")) as client:
                return await client.reply_to_thread(str(board), str(thread_id), str(content), str(challenge_id), str(result_hash), sage=sage)

        result = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "reply_to_thread"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "reply_to_thread"}
    return {"ok": True, "data": result, "action": "reply_to_thread"}


# --- Moltbook ---

def _handler_moltbook_get_feed(call: ToolCall) -> Dict[str, Any]:
    limit = _get(call, "limit", 15)
    limit = min(int(limit), 100) if limit is not None else 15
    sort = _get(call, "sort", "new")
    if sort not in ("hot", "new", "top"):
        sort = "new"

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"posts": []}, "count": 0, "action": "get_feed"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import get_feed
        result = get_feed(sort=sort, limit=limit)
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_feed"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_feed"}
    posts = result.get("posts", []) if isinstance(result, dict) else []
    return {"ok": True, "data": result, "count": len(posts), "action": "get_feed"}


def _handler_moltbook_get_reply_activity(call: ToolCall) -> Dict[str, Any]:
    post_limit = _get(call, "post_limit", 10)
    post_limit = min(int(post_limit), 25) if post_limit is not None else 10
    sort = _get(call, "sort", "new")
    if sort not in ("top", "new", "controversial"):
        sort = "new"

    if not _real_social_apis_enabled():
        return {
            "ok": True,
            "data": {
                "agent_name": None,
                "scanned_posts": 0,
                "reply_to_post_count": 0,
                "reply_to_reply_count": 0,
                "items": [],
            },
            "action": "get_reply_activity",
        }

    try:
        from hg_platforms.moltbook.moltbook_api_client import get_recent_reply_activity
        result = get_recent_reply_activity(
            agent_name=_get(call, "agent_name"),
            post_limit=post_limit,
            sort=sort,
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_reply_activity"}

    if isinstance(result, dict) and not result.get("ok", True):
        return {"ok": False, "error": result.get("error"), "action": "get_reply_activity"}
    return {"ok": True, "data": result.get("data", {}), "action": "get_reply_activity"}


def _handler_moltbook_get_post(call: ToolCall) -> Dict[str, Any]:
    post_id = _get(call, "post_id")
    if not post_id:
        return {"ok": False, "error": "post_id is required", "action": "get_post"}

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"thread": {"id": str(post_id), "content": "", "author": ""}}, "action": "get_post"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import get_post
        result = get_post(str(post_id))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_post"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_post"}
    return {"ok": True, "data": result, "action": "get_post"}


def _handler_moltbook_get_comments(call: ToolCall) -> Dict[str, Any]:
    post_id = _get(call, "post_id")
    if not post_id:
        return {"ok": False, "error": "post_id is required", "action": "get_comments"}

    if not _real_social_apis_enabled():
        return {"ok": True, "data": {"comments": []}, "count": 0, "action": "get_comments"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import get_comments
        result = get_comments(str(post_id), sort=str(_get(call, "sort", "new")))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "get_comments"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "get_comments"}
    comments = result.get("comments", []) if isinstance(result, dict) else []
    return {"ok": True, "data": result, "count": len(comments), "action": "get_comments"}


def _handler_moltbook_create_post(call: ToolCall) -> Dict[str, Any]:
    title = _get(call, "title")
    content = _get(call, "content")
    if not title or not content:
        return {"ok": False, "error": "title and content are required", "action": "create_post"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "create_post"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import create_post
        result = create_post(
            title=str(title),
            content=str(content),
            submolt=str(_get(call, "submolt", "general") or "general"),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "create_post"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "create_post"}
    return {"ok": True, "data": result, "action": "create_post"}


def _handler_moltbook_post_comment(call: ToolCall) -> Dict[str, Any]:
    post_id = _get(call, "post_id")
    content = _get(call, "content")
    parent_id = _get(call, "parent_id")
    if not post_id or not content:
        return {"ok": False, "error": "post_id and content are required", "action": "create_comment"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "create_comment"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import create_comment
        result = create_comment(
            post_id=str(post_id),
            content=str(content),
            parent_id=str(parent_id) if parent_id else None,
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "create_comment"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "create_comment"}
    return {"ok": True, "data": result, "action": "create_comment"}


def _handler_moltbook_vote_comment(call: ToolCall) -> Dict[str, Any]:
    comment_id = _get(call, "comment_id")
    vote = str(_get(call, "vote", "upvote") or "upvote").lower()
    if not comment_id:
        return {"ok": False, "error": "comment_id is required", "action": "vote_comment"}
    if vote not in ("upvote", "downvote"):
        return {"ok": False, "error": "vote must be upvote or downvote", "action": "vote_comment"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "vote_comment"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import upvote_comment, downvote_comment
        result = upvote_comment(str(comment_id)) if vote == "upvote" else downvote_comment(str(comment_id))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "vote_comment"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "vote_comment"}
    return {"ok": True, "data": result, "action": "vote_comment"}


def _handler_moltbook_vote_post(call: ToolCall) -> Dict[str, Any]:
    post_id = _get(call, "post_id")
    vote = str(_get(call, "vote", "upvote") or "upvote").lower()
    if not post_id:
        return {"ok": False, "error": "post_id is required", "action": "vote_post"}
    if vote not in ("upvote", "downvote"):
        return {"ok": False, "error": "vote must be upvote or downvote", "action": "vote_post"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "vote_post"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import downvote_post, upvote_post
        result = upvote_post(str(post_id)) if vote == "upvote" else downvote_post(str(post_id))
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "vote_post"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "vote_post"}
    return {"ok": True, "data": result, "action": "vote_post"}


def _handler_moltbook_verify_post(call: ToolCall) -> Dict[str, Any]:
    post_id = _get(call, "post_id", "")
    verification_code = _get(call, "verification_code")
    answer = _get(call, "answer")
    if not verification_code or not answer:
        return {"ok": False, "error": "verification_code and answer are required", "action": "verify_post"}

    if not _real_social_apis_enabled():
        return {"ok": False, "error": "real_apis_disabled", "action": "verify_post"}

    try:
        from hg_platforms.moltbook.moltbook_api_client import verify_post
        result = verify_post(
            post_id=str(post_id) if post_id else "",
            verification_code=str(verification_code),
            answer=str(answer),
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "action": "verify_post"}

    if isinstance(result, dict) and result.get("error"):
        return {"ok": False, "error": result["error"], "action": "verify_post"}
    return {"ok": True, "data": result, "action": "verify_post"}


# Map tool_name -> handler for registration
SOCIAL_TOOL_HANDLERS: Dict[str, Callable[[ToolCall], Dict[str, Any]]] = {
    "social.fourclaw.getposts": _handler_fourclaw_getposts,
    "social.fourclaw.get_thread": _handler_fourclaw_get_thread,
    "social.fourclaw.create_thread": _handler_fourclaw_create_thread,
    "social.fourclaw.reply": _handler_fourclaw_reply,
    "social.aichan.getposts": _handler_aichan_getposts,
    "social.aichan.get_thread": _handler_aichan_get_thread,
    "social.aichan.create_thread": _handler_aichan_create_thread,
    "social.aichan.reply": _handler_aichan_reply,
    "social.agentchan.getposts": _handler_agentchan_getposts,
    "social.agentchan.get_thread": _handler_agentchan_get_thread,
    "social.agentchan.get_replies": _handler_agentchan_get_replies,
    "social.agentchan.create_thread": _handler_agentchan_create_thread,
    "social.agentchan.reply": _handler_agentchan_reply,
    "social.moltbook.get_feed": _handler_moltbook_get_feed,
    "social.moltbook.get_post": _handler_moltbook_get_post,
    "social.moltbook.get_comments": _handler_moltbook_get_comments,
    "social.moltbook.get_reply_activity": _handler_moltbook_get_reply_activity,
    "social.moltbook.create_post": _handler_moltbook_create_post,
    "social.moltbook.post_comment": _handler_moltbook_post_comment,
    "social.moltbook.vote_post": _handler_moltbook_vote_post,
    "social.moltbook.vote_comment": _handler_moltbook_vote_comment,
    "social.moltbook.verify_post": _handler_moltbook_verify_post,
}

# Minimal schemas for tool registry (optional; router only needs handler)
SOCIAL_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "social.fourclaw.getposts": {"board": "string", "limit": "number", "include_media": "boolean", "include_content": "boolean"},
    "social.fourclaw.get_thread": {"thread_id": "string"},
    "social.fourclaw.create_thread": {"board": "string", "title": "string", "content": "string"},
    "social.fourclaw.reply": {"thread_id": "string", "content": "string"},
    "social.aichan.getposts": {"board": "string"},
    "social.aichan.get_thread": {"board": "string", "thread_id": "string"},
    "social.aichan.create_thread": {"board": "string", "subject": "string", "title": "string", "content": "string", "body": "string"},
    "social.aichan.reply": {"board": "string", "thread_id": "string", "content": "string", "body": "string"},
    "social.agentchan.getposts": {"board": "string", "limit": "number", "task_name": "string"},
    "social.agentchan.get_thread": {"board": "string", "thread_id": "string", "task_name": "string"},
    "social.agentchan.get_replies": {"since": "number", "task_name": "string"},
    "social.agentchan.create_thread": {"board": "string", "subject": "string", "title": "string", "content": "string", "challenge_id": "string", "result_hash": "string", "task_name": "string"},
    "social.agentchan.reply": {"board": "string", "thread_id": "string", "content": "string", "challenge_id": "string", "result_hash": "string", "sage": "boolean", "task_name": "string"},
    "social.moltbook.get_feed": {"limit": "number", "sort": "string"},
    "social.moltbook.get_post": {"post_id": "string"},
    "social.moltbook.get_comments": {"post_id": "string", "sort": "string"},
    "social.moltbook.get_reply_activity": {"agent_name": "string", "post_limit": "number", "sort": "string"},
    "social.moltbook.create_post": {"title": "string", "content": "string", "submolt": "string"},
    "social.moltbook.post_comment": {"post_id": "string", "content": "string", "parent_id": "string"},
    "social.moltbook.vote_post": {"post_id": "string", "vote": "string"},
    "social.moltbook.vote_comment": {"comment_id": "string", "vote": "string"},
    "social.moltbook.verify_post": {"post_id": "string", "verification_code": "string", "answer": "string"},
}
