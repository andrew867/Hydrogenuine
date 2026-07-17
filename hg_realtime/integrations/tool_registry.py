"""Concrete tool registry: tool_name -> (handler, schema, options). No stub."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .tool_router import ToolCall


@dataclass
class ToolEntry:
    """Handler + schema + options for one tool."""
    handler: Callable[[ToolCall], Dict[str, Any]]
    schema: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Concrete registry: register(tool_name, handler, schema?, options?), get(tool_name) -> ToolEntry."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolEntry] = {}

    def register(
        self,
        tool_name: str,
        handler: Callable[[ToolCall], Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("tool_name must be a non-empty string")
        if not callable(handler):
            raise ValueError("handler must be callable")
        self._tools[tool_name] = ToolEntry(
            handler=handler,
            schema=dict(schema) if schema else {},
            options=dict(options) if options else {},
        )

    def get(self, tool_name: str) -> ToolEntry:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        return self._tools[tool_name]

    def resolve(self, tool_name: str) -> Optional[ToolEntry]:
        return self._tools.get(tool_name)

    def list_names(self) -> List[str]:
        return sorted(self._tools.keys())


def _not_implemented_handler(call: ToolCall) -> Dict[str, Any]:
    return {"ok": False, "error": "not_implemented", "tool_name": call.tool_name}


def build_default_registry() -> ToolRegistry:
    """Registry with all L10 tool names. Social (Phase 6), file/search (Phase 7), office (Phase 11)."""
    from . import social_tools
    from . import file_tools
    from . import search_tools
    from . import office_tools

    reg = ToolRegistry()
    for name, handler in social_tools.SOCIAL_TOOL_HANDLERS.items():
        reg.register(
            name,
            handler,
            schema=social_tools.SOCIAL_TOOL_SCHEMAS.get(name, {}),
            options={},
        )
    reg.register("file.parse", file_tools.handler_file_parse, schema={"path": "string"}, options={})
    reg.register("search.query", search_tools.handler_search_query, schema={"q": "string", "query": "string"}, options={})
    reg.register(
        "web.search_brave",
        search_tools.handler_web_search_brave,
        schema={"query": "string", "q": "string", "count": "integer", "freshness": "string", "tenant_id": "string"},
        options={},
    )
    reg.register(
        "brave.web.search",
        search_tools.handler_brave_web_search,
        schema={"query": "string", "q": "string", "count": "integer", "freshness": "string", "tenant_id": "string"},
        options={},
    )
    reg.register(
        "brave.web.search_post",
        search_tools.handler_brave_web_search_post,
        schema={"query": "string", "q": "string", "count": "integer", "freshness": "string", "tenant_id": "string"},
        options={},
    )
    reg.register(
        "brave.news.search",
        search_tools.handler_brave_news_search,
        schema={"query": "string", "q": "string", "count": "integer", "freshness": "string", "tenant_id": "string"},
        options={},
    )
    reg.register(
        "brave.news.search_post",
        search_tools.handler_brave_news_search_post,
        schema={"query": "string", "q": "string", "count": "integer", "freshness": "string", "tenant_id": "string"},
        options={},
    )
    reg.register(
        "brave.answers",
        search_tools.handler_brave_answers,
        schema={"prompt": "string", "query": "string", "q": "string", "model": "string"},
        options={},
    )
    reg.register("search.fetch_url", search_tools.handler_search_fetch_url, schema={"url": "string"}, options={})
    # Office tool pack (Phase 11): path (+ optional workspace); write tools also take content/data.
    _office_schema_path_workspace = {"path": "string", "workspace": "string"}
    reg.register("office.docx.read", office_tools.handler_office_docx_read, schema=_office_schema_path_workspace, options={})
    reg.register("office.docx.write", office_tools.handler_office_docx_write, schema={**_office_schema_path_workspace, "content": "string|list"}, options={})
    reg.register("office.xlsx.read", office_tools.handler_office_xlsx_read, schema=_office_schema_path_workspace, options={})
    reg.register("office.xlsx.write", office_tools.handler_office_xlsx_write, schema={**_office_schema_path_workspace, "data": "list|dict"}, options={})
    reg.register("office.pptx.read", office_tools.handler_office_pptx_read, schema=_office_schema_path_workspace, options={})
    reg.register("office.pptx.write", office_tools.handler_office_pptx_write, schema={**_office_schema_path_workspace, "content": "string|list"}, options={})
    reg.register("office.pdf.read", office_tools.handler_office_pdf_read, schema=_office_schema_path_workspace, options={})
    return reg
