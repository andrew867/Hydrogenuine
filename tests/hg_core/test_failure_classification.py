"""Unit tests for autonomy Phase 0: failure classification (F1).

Each F1 class must be producible from appropriate exception/context;
classify_failure returns failure_class, message, and minimal context.
"""

import pytest

# Will be implemented in hg_core.task_graph.failure_classification
try:
    from hg_core.task_graph.failure_classification import (
        classify_failure,
        FAILURE_CLASSES,
    )
except ImportError:
    classify_failure = None
    FAILURE_CLASSES = ()


FAILURE_CLASSES_EXPECTED = [
    "transient_network",
    "rate_limited",
    "dependency_unavailable",
    "validation_failed",
    "safety_blocked",
    "permission_denied",
    "timeout",
    "internal_error",
    "unknown",
]


@pytest.mark.skipif(classify_failure is None, reason="failure_classification module not yet implemented")
class TestFailureClassificationMapping:
    """For each failure class, at least one test that produces that class."""

    def test_transient_network(self):
        import urllib.error
        exc = urllib.error.URLError("Connection refused")
        result = classify_failure(exc, {"node_id": "n1"})
        assert result["failure_class"] == "transient_network"
        assert "message" in result
        assert "context" in result

    def test_rate_limited(self):
        class RateLimitError(Exception):
            pass
        exc = RateLimitError("429 Too Many Requests")
        result = classify_failure(exc, {"node_id": "n1"})
        assert result["failure_class"] == "rate_limited"
        assert "message" in result

    def test_dependency_unavailable(self):
        exc = FileNotFoundError("memory/automation/foo/context.json")
        result = classify_failure(exc, {})
        assert result["failure_class"] == "dependency_unavailable"
        assert "message" in result

    def test_validation_failed(self):
        exc = ValueError("Invalid input: missing field 'goal'")
        result = classify_failure(exc, {"node_id": "n1"})
        assert result["failure_class"] == "validation_failed"
        assert "message" in result

    def test_safety_blocked(self):
        exc = RuntimeError("safety_blocked: content policy violation")
        result = classify_failure(exc, {"node_id": "post"})
        assert result["failure_class"] == "safety_blocked"
        assert "message" in result

    def test_permission_denied(self):
        exc = PermissionError("Scope not allowed: write external")
        result = classify_failure(exc, {})
        assert result["failure_class"] == "permission_denied"
        assert "message" in result

    def test_timeout(self):
        exc = TimeoutError("Operation timed out after 30s")
        result = classify_failure(exc, {"node_id": "n1"})
        assert result["failure_class"] == "timeout"
        assert "message" in result

    def test_internal_error(self):
        exc = RuntimeError("Unexpected state in executor")
        result = classify_failure(exc, {"node_id": "n1"})
        assert result["failure_class"] == "internal_error"
        assert "message" in result

    def test_unknown_fallback(self):
        exc = Exception("Something else")
        result = classify_failure(exc, {})
        assert result["failure_class"] == "unknown"
        assert "message" in result


@pytest.mark.skipif(classify_failure is None, reason="failure_classification module not yet implemented")
def test_classify_returns_shape():
    """classify_failure returns dict with failure_class, message, context."""
    result = classify_failure(ValueError("test"), {"node_id": "n1"})
    assert isinstance(result, dict)
    assert "failure_class" in result
    assert "message" in result
    assert "context" in result
    assert result["failure_class"] in FAILURE_CLASSES_EXPECTED


@pytest.mark.skipif(classify_failure is None, reason="failure_classification module not yet implemented")
def test_failure_classes_constant():
    """FAILURE_CLASSES contains all expected F1 classes."""
    assert set(FAILURE_CLASSES) == set(FAILURE_CLASSES_EXPECTED)
