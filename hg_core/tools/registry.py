"""
Tool registry for entity tools (Social Media Entity Tools).
Bootstrap includes brave/search (from tool_contract_setup), social_reddit, social_x, social_facebook, browser_runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolDefinition:
    tool_id: str
    category: str
    display_name: str
    read_only: bool = True
    requires_approval: bool = False
    requires_browser: bool = False
    requires_network: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Alias for tool_id for planner compatibility."""
        return self.tool_id


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def list_all(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def list(self) -> List[ToolDefinition]:
        """Alias for list_all() for planner compatibility."""
        return self.list_all()

    def list_for_planner(self) -> List[Dict[str, Any]]:
        return [
            {
                "tool_id": t.tool_id,
                "category": t.category,
                "display_name": t.display_name,
                "read_only": t.read_only,
                "requires_approval": t.requires_approval,
                "requires_browser": t.requires_browser,
                "requires_network": t.requires_network,
                "metadata": t.metadata,
            }
            for t in self._tools.values()
        ]


def _bootstrap_file_and_search(reg: ToolRegistry) -> None:
    """Register brave/search tools (reuse names from tool_contract_setup, do not duplicate impl)."""
    from hg_core.task_graph.tool_contract_setup import FILE_AND_SEARCH_TOOL_NAMES
    for name in FILE_AND_SEARCH_TOOL_NAMES:
        reg.register(ToolDefinition(
            tool_id=name,
            category="search",
            display_name=name.replace(".", " ").title(),
            read_only=True,
            requires_approval=False,
            requires_browser=False,
            requires_network=True,
            metadata={},
        ))


def _bootstrap_social_browser(reg: ToolRegistry) -> None:
    """Register social and browser entity tools."""
    reg.register(ToolDefinition(
        tool_id="social_reddit",
        category="social",
        display_name="Reddit",
        read_only=False,
        requires_approval=True,
        requires_browser=False,
        requires_network=True,
        metadata={"platform": "reddit"},
    ))
    reg.register(ToolDefinition(
        tool_id="social_x",
        category="social",
        display_name="X (Twitter)",
        read_only=False,
        requires_approval=True,
        requires_browser=False,
        requires_network=True,
        metadata={"platform": "x"},
    ))
    reg.register(ToolDefinition(
        tool_id="social_facebook",
        category="social",
        display_name="Facebook",
        read_only=False,
        requires_approval=True,
        requires_browser=False,
        requires_network=True,
        metadata={"platform": "facebook"},
    ))
    reg.register(ToolDefinition(
        tool_id="browser_runtime",
        category="browser",
        display_name="Browser runtime",
        read_only=False,
        requires_approval=True,
        requires_browser=True,
        requires_network=True,
        metadata={},
    ))


def get_default_registry() -> ToolRegistry:
    """Return a registry with brave/search + social + browser tools bootstrapped."""
    reg = ToolRegistry()
    _bootstrap_file_and_search(reg)
    _bootstrap_social_browser(reg)
    return reg
