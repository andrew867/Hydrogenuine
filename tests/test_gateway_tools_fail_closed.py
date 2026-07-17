"""Gateway tool runtime fail-closed behavior (R3)."""
from __future__ import annotations

import os

import pytest

import hg_gateway.tools as gateway_tools


@pytest.fixture(autouse=True)
def _reset_gateway_tools():
    gateway_tools._registry = None
    gateway_tools._adapter = None
    gateway_tools._build_mode = "uninitialized"
    gateway_tools._build_error = None
    yield
    gateway_tools._registry = None
    gateway_tools._adapter = None
    gateway_tools._build_mode = "uninitialized"
    gateway_tools._build_error = None


def test_invoke_blocks_non_echo_when_stub_fallback_active(monkeypatch):
    monkeypatch.setattr(
        gateway_tools,
        "get_runtime_diagnostics",
        lambda: {
            "stub_fallback_active": True,
            "build_error": "simulated contract failure",
        },
    )
    out = gateway_tools.invoke_tool("fourclaw-auto-post", {"goal": "test"})
    assert out["ok"] is False
    assert out["error"]["code"] == "tool_runtime_unavailable"


def test_strict_build_raises_when_contract_fails(monkeypatch):
    os.environ["HG_ENV"] = "Production"
    os.environ.pop("HG_GATEWAY_DEV", None)
    monkeypatch.setattr(
        "hg_core.task_graph.tool_contract_setup.build_default_tool_contract",
        lambda: (_ for _ in ()).throw(RuntimeError("contract broken")),
    )
    with pytest.raises(RuntimeError, match="refuses stub tool adapter fallback"):
        gateway_tools._build()
