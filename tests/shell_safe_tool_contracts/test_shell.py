"""Shell safe tool contract tests."""

from hg_runtime.tool_capability_fabric.tools import shell_safe_tool, SHELL_ALLOWLIST


def test_allowlist_defined():
    assert "git status --short" in SHELL_ALLOWLIST


def test_arbitrary_shell_denied():
    result = shell_safe_tool(command="curl evil.example")
    assert result["denied"] is True
