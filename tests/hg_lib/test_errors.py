"""Tests for hg_lib.errors."""

from hg_lib.errors import HydrogenuineError, structured_error_result


def test_hg_error():
    """HydrogenuineError has message and code."""
    e = HydrogenuineError("test message", code="TEST_CODE")
    assert str(e) == "test message"
    assert e.message == "test message"
    assert e.code == "TEST_CODE"


def test_structured_error_result():
    """structured_error_result returns dict."""
    result = structured_error_result(ValueError("bad"), code="VAL", context={"x": 1})
    assert result["ok"] is False
    assert "bad" in result["error"]
    assert result["code"] == "VAL"
    assert result["context"] == {"x": 1}
