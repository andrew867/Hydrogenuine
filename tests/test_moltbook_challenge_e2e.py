"""
Pack2-10: Moltbook two-tool flow e2e. Real fake server, real run_task_tool, no mocks.
Tool 1 post_or_reply -> challenge; tool 2 submit_verification with answer.
"""

import importlib.util
import pytest
from pathlib import Path


def _load_moltbook_fake():
    """Load tools/test_servers/moltbook_fake without requiring tools as a package."""
    root = Path(__file__).resolve().parent.parent
    path = root / "tools" / "test_servers" / "moltbook_fake.py"
    spec = importlib.util.spec_from_file_location("moltbook_fake", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_moltbook_two_tool_flow_e2e():
    """Start fake server; run moltbook.post_or_reply (get challenge); run moltbook.submit_verification (answer); real data."""
    moltbook_fake = _load_moltbook_fake()
    server, port = moltbook_fake.run_fake_server(port=0)
    try:
        base_url = f"http://127.0.0.1:{port}/api/v1"
        from hg_core.task_graph.native_task_tools import run_task_tool

        # Tool 1: attempt post -> receive challenge
        r1 = run_task_tool(
            "moltbook.post_or_reply",
            {"base_url": base_url, "content": "E2E test post"},
            timeout_s=30,
        )
        assert r1 is not None
        assert r1.get("ok") is False
        outputs = r1.get("outputs") or {}
        assert "challenge" in outputs
        ch = outputs["challenge"]
        assert ch.get("verification_code")
        assert ch.get("challenge_prompt")
        assert ch.get("validation_endpoint")

        # Tool 2: submit verification (answer from "chat" — known answer for fake server)
        r2 = run_task_tool(
            "moltbook.submit_verification",
            {
                "validation_endpoint": ch["validation_endpoint"],
                "verification_code": ch["verification_code"],
                "answer": "5.00",
            },
            timeout_s=30,
        )
        assert r2 is not None
        assert r2.get("ok") is True
    finally:
        server.shutdown()


def test_moltbook_post_or_reply_returns_challenge_structure():
    """Tool 1 challenge payload has required fields for chat to reason and tool 2 to submit."""
    moltbook_fake = _load_moltbook_fake()
    server, port = moltbook_fake.run_fake_server(port=0)
    try:
        from hg_core.task_graph.native_task_tools import run_task_tool
        base_url = f"http://127.0.0.1:{port}/api/v1"
        r = run_task_tool("moltbook.post_or_reply", {"base_url": base_url, "content": "x"}, timeout_s=10)
        assert r and r.get("ok") is False
        ch = (r.get("outputs") or {}).get("challenge")
        assert ch is not None
        assert "challenge_id" in ch
        assert "challenge_prompt" in ch
        assert "verification_code" in ch
        assert "validation_endpoint" in ch
    finally:
        server.shutdown()
