"""Tests for the dependency-override reset isolation (CQB3 tranche 3).

Gateway/operator tests bypass auth via `app.dependency_overrides[...]` on the shared
module-level app. Without a per-test reset, a leaked override contaminates later tests
on the same xdist worker (spurious 403). The autouse `_reset_app_dependency_overrides`
fixture in tests/conftest.py clears overrides before + after each test.
"""
from __future__ import annotations

from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, verify_admin_key


def test_override_leak_part1_sets_override():
    # Simulate a test that (accidentally) leaves an override set and does NOT clean up.
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[verify_admin_key] = lambda: None
    assert verify_api_key in app.dependency_overrides


def test_override_leak_part2_starts_clean():
    # The autouse reset must have cleared part1's leaked overrides before this test.
    assert verify_api_key not in app.dependency_overrides
    assert verify_admin_key not in app.dependency_overrides


def test_authorized_override_works_within_a_test():
    # Within a single test, an override set here is honoured (reset only fires at
    # test boundaries, not mid-test).
    app.dependency_overrides[verify_api_key] = lambda: None
    assert app.dependency_overrides.get(verify_api_key) is not None


def test_next_test_still_clean_after_previous_override():
    assert verify_api_key not in app.dependency_overrides
