"""Search/news tool contract tests."""

from hg_runtime.tool_capability_fabric.registry import load_registry


def test_web_search_disabled():
    reg = load_registry()
    cap = reg.get("web_search")
    assert cap is not None
    assert cap.enabled is False


def test_news_search_disabled():
    reg = load_registry()
    cap = reg.get("news_search")
    assert cap.enabled is False
