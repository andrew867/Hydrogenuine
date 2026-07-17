"""Tool registry: resolve for known tools."""

import pytest

from hg_realtime.integrations.tool_registry import ToolRegistry, build_default_registry
from hg_realtime.integrations.tool_router import ToolCall


def test_registry_resolve_known_tools():
    reg = build_default_registry()
    entry = reg.get("social.fourclaw.getposts")
    assert entry is not None
    assert isinstance(entry.schema, dict)
    assert callable(entry.handler)
    entry = reg.resolve("file.parse")
    assert entry is not None
    with pytest.raises(KeyError):
        reg.get("unknown.tool.xyz")


def test_registry_register_and_get():
    reg = ToolRegistry()

    def my_handler(call):
        return {"ok": True, "value": call.args.get("x")}

    reg.register("my.tool", my_handler, schema={"type": "object"}, options={"timeout": 30})
    entry = reg.get("my.tool")
    assert entry.handler is my_handler
    assert entry.schema == {"type": "object"}
    assert entry.options == {"timeout": 30}
    result = entry.handler(
        ToolCall(tool_name="my.tool", args={"x": 1}, idempotency_key="key12345678", correlation_id="c", run_id="r")
    )
    assert result == {"ok": True, "value": 1}


def test_web_search_brave_registered():
    reg = build_default_registry()
    entry = reg.get("web.search_brave")
    assert entry is not None
    assert callable(entry.handler)
    assert reg.get("brave.web.search") is not None
    assert reg.get("brave.web.search_post") is not None
    assert reg.get("brave.news.search") is not None
    assert reg.get("brave.news.search_post") is not None
    assert reg.get("brave.answers") is not None


def test_web_search_brave_missing_query_returns_error():
    from hg_realtime.integrations.search_tools import handler_web_search_brave
    from hg_realtime.integrations.tool_router import ToolCall
    call = ToolCall(tool_name="web.search_brave", args={}, idempotency_key="k", correlation_id="c", run_id="r")
    result = handler_web_search_brave(call)
    assert result.get("ok") is False
    assert "query" in result.get("error", "").lower() or "q" in result.get("error", "").lower()


def test_web_search_brave_returns_normalized_shape():
    """Without BRAVE_API_KEY, _brave_web_search returns []; handler still returns ok with empty results."""
    from hg_realtime.integrations.search_tools import handler_web_search_brave
    from hg_realtime.integrations.tool_router import ToolCall
    call = ToolCall(
        tool_name="web.search_brave",
        args={"query": "test query"},
        idempotency_key="k",
        correlation_id="c",
        run_id="r",
    )
    result = handler_web_search_brave(call)
    assert result.get("ok") is True
    assert "data" in result
    assert "results" in result["data"]
    assert "query" in result["data"]
    assert result["data"]["count"] == len(result["data"]["results"])
    assert result.get("action") == "web.search_brave"


def test_web_search_brave_count_capped_at_10():
    from hg_realtime.integrations.search_tools import _normalize_count, MAX_COUNT
    assert _normalize_count(99) == MAX_COUNT


def test_brave_news_search_returns_normalized_shape(monkeypatch):
    from hg_realtime.integrations.search_tools import handler_brave_news_search
    from hg_realtime.integrations.tool_router import ToolCall

    monkeypatch.setattr(
        "hg_realtime.integrations.search_tools._run_brave_search",
        lambda kind, **kwargs: [{"title": "Headline", "url": "https://example.com", "description": "Summary"}],
    )
    call = ToolCall(tool_name="brave.news.search", args={"query": "iran news"}, idempotency_key="k", correlation_id="c", run_id="r")
    result = handler_brave_news_search(call)
    assert result["ok"] is True
    assert result["data"]["kind"] == "news"
    assert result["data"]["count"] == 1


def test_brave_answers_missing_prompt_returns_error():
    from hg_realtime.integrations.search_tools import handler_brave_answers
    from hg_realtime.integrations.tool_router import ToolCall

    call = ToolCall(tool_name="brave.answers", args={}, idempotency_key="k", correlation_id="c", run_id="r")
    result = handler_brave_answers(call)
    assert result["ok"] is False


def test_fetch_url_ssrf_denies_private_ip():
    """search.fetch_url with private/localhost URL returns ok=False (SSRF-safe)."""
    from hg_realtime.integrations.search_tools import handler_search_fetch_url
    from hg_realtime.integrations.tool_router import ToolCall
    for bad_url in ("http://127.0.0.1/", "http://localhost/", "http://192.168.1.1/", "http://169.254.169.254/"):
        call = ToolCall(
            tool_name="search.fetch_url",
            args={"url": bad_url},
            idempotency_key="k",
            correlation_id="c",
            run_id="r",
        )
        result = handler_search_fetch_url(call)
        assert result.get("ok") is False
        assert "denied" in result.get("error", "").lower() or "url_resolved" in result.get("error", "")


def test_fetch_url_is_ip_allowed():
    from hg_realtime.integrations.search_tools import _is_ip_allowed
    assert _is_ip_allowed("127.0.0.1") is False
    assert _is_ip_allowed("::1") is False
    assert _is_ip_allowed("10.0.0.1") is False
    assert _is_ip_allowed("192.168.1.1") is False
    assert _is_ip_allowed("169.254.169.254") is False
    assert _is_ip_allowed("8.8.8.8") is True
    assert _is_ip_allowed("1.1.1.1") is True
