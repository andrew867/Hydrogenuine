"""Tests for office tool pack (Phase 11): docx, xlsx, pptx, pdf read/write."""

import tempfile
from pathlib import Path

import pytest

from hg_realtime.integrations.tool_registry import build_default_registry
from hg_realtime.integrations.tool_router import ToolCall, execute
from hg_realtime.integrations.office_tools import (
    handler_office_docx_read,
    handler_office_docx_write,
    handler_office_xlsx_read,
    handler_office_xlsx_write,
    handler_office_pptx_read,
    handler_office_pptx_write,
    handler_office_pdf_read,
    idempotency_key_office,
)
from hg_realtime.integrations.idempotency_store import InMemoryIdempotencyStore


def _call(tool_name: str, args: dict, idempotency_key: str = "office-test-key-12345678") -> ToolCall:
    return ToolCall(tool_name=tool_name, args=args, idempotency_key=idempotency_key, correlation_id="c", run_id="r")


def test_registry_resolves_office_tools():
    reg = build_default_registry()
    for name in (
        "office.docx.read",
        "office.docx.write",
        "office.xlsx.read",
        "office.xlsx.write",
        "office.pptx.read",
        "office.pptx.write",
        "office.pdf.read",
    ):
        entry = reg.resolve(name)
        assert entry is not None, name
        assert callable(entry.handler)


def test_idempotency_key_office():
    k = idempotency_key_office("/path/to/file.docx", "read")
    assert isinstance(k, str) and len(k) >= 8
    assert k == idempotency_key_office("/path/to/file.docx", "read")


# --- docx (requires python-docx) ---


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("docx") is None,
    reason="python-docx not installed",
)
def test_office_docx_write_read_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path_arg = "test.docx"
        call_write = _call("office.docx.write", {"path": path_arg, "workspace": tmp, "content": ["Hello", "World"]})
        out = handler_office_docx_write(call_write)
        assert out.get("ok") is True
        full = Path(tmp) / path_arg
        assert full.exists()
        call_read = _call("office.docx.read", {"path": path_arg, "workspace": tmp})
        out_read = handler_office_docx_read(call_read)
        assert out_read.get("ok") is True
        data = out_read.get("data", {})
        assert "paragraphs" in data
        assert "Hello" in data["paragraphs"] and "World" in data["paragraphs"]


def test_office_docx_read_missing_path():
    out = handler_office_docx_read(_call("office.docx.read", {}))
    assert out.get("ok") is False
    assert "path" in (out.get("error") or "").lower() or "invalid" in (out.get("error") or "").lower()


# --- xlsx (requires openpyxl) ---


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("openpyxl") is None,
    reason="openpyxl not installed",
)
def test_office_xlsx_write_read_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path_arg = "test.xlsx"
        data = {"Sheet1": [["A", "B"], [1, 2]]}
        call_write = _call("office.xlsx.write", {"path": path_arg, "workspace": tmp, "data": data})
        out = handler_office_xlsx_write(call_write)
        assert out.get("ok") is True
        assert (Path(tmp) / path_arg).exists()
        call_read = _call("office.xlsx.read", {"path": path_arg, "workspace": tmp})
        out_read = handler_office_xlsx_read(call_read)
        assert out_read.get("ok") is True
        got = out_read.get("data", {})
        assert "sheets" in got and "Sheet1" in got["sheets"]
        assert got["sheets"]["Sheet1"][0] == ["A", "B"]


def test_office_xlsx_write_missing_data():
    with tempfile.TemporaryDirectory() as tmp:
        out = handler_office_xlsx_write(_call("office.xlsx.write", {"path": "out.xlsx", "workspace": tmp}))
        assert out.get("ok") is False
        assert "data" in (out.get("error") or "").lower()


# --- pptx (requires python-pptx) ---


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pptx") is None,
    reason="python-pptx not installed",
)
def test_office_pptx_write_read_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path_arg = "test.pptx"
        call_write = _call("office.pptx.write", {"path": path_arg, "workspace": tmp, "content": ["Slide one", "Slide two"]})
        out = handler_office_pptx_write(call_write)
        assert out.get("ok") is True
        assert (Path(tmp) / path_arg).exists()
        call_read = _call("office.pptx.read", {"path": path_arg, "workspace": tmp})
        out_read = handler_office_pptx_read(call_read)
        assert out_read.get("ok") is True
        data = out_read.get("data", {})
        assert "slides" in data and len(data["slides"]) >= 1


# --- pdf (read-only; requires pypdf) ---


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pypdf") is None,
    reason="pypdf not installed",
)
def test_office_pdf_read_missing_file():
    out = handler_office_pdf_read(_call("office.pdf.read", {"path": "/nonexistent/file.pdf"}))
    assert out.get("ok") is False


def test_office_execute_via_registry_docx_write():
    """Execute office.docx.write through registry + router returns ok/data structure."""
    reg = build_default_registry()
    store = InMemoryIdempotencyStore()
    with tempfile.TemporaryDirectory() as tmp:
        call = _call("office.docx.write", {"path": "exec.docx", "workspace": tmp, "content": "Single paragraph"})
        result = execute(call, reg, store)
        assert isinstance(result, dict)
        assert "ok" in result
        if result.get("ok"):
            assert "data" in result
        else:
            assert "error" in result
