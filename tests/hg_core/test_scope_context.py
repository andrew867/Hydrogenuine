"""
Tests for scope_context: set_scope, get_scope, scope_context (contextvars).
Co-access (molecules) layer: scope propagation for grouping reads into rooms.
"""

import pytest

from hg_core.scope_context import set_scope, get_scope, clear_scope, scope_context


def test_get_scope_empty_by_default():
    """get_scope returns empty dict when no scope set."""
    clear_scope()
    assert get_scope() == {}


def test_set_scope_and_get_scope():
    """set_scope sets scope; get_scope returns it."""
    clear_scope()
    set_scope("session", "automation-test", session_id="automation-test")
    scope = get_scope()
    assert scope.get("scope_type") == "session"
    assert scope.get("scope_id") == "automation-test"
    assert scope.get("session_id") == "automation-test"
    clear_scope()
    assert get_scope() == {}


def test_scope_context_manager():
    """scope_context sets scope for the block and restores previous on exit."""
    clear_scope()
    set_scope("run", "run-1", run_id="run-1")
    with scope_context(scope_type="session", scope_id="s2", session_id="s2"):
        scope = get_scope()
        assert scope.get("scope_type") == "session"
        assert scope.get("scope_id") == "s2"
    scope_after = get_scope()
    assert scope_after.get("scope_type") == "run"
    assert scope_after.get("scope_id") == "run-1"
    clear_scope()
