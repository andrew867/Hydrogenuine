"""Regression tests for the hg_gateway.store singleton reset (CQB2 tranche 2).

The store caches a module-level singleton keyed to HG_GATEWAY_STORE / HG_GATEWAY_DB_PATH
at first construction. Without a per-test reset, xdist workers leak a stale store across
tests (nondeterministic "not found" stragglers). reset_store_for_tests() + the autouse
conftest fixture restore isolation.
"""
from __future__ import annotations

import hg_gateway.store as store_module
from hg_gateway.store import get_store, reset_store_for_tests


def test_get_store_respects_changed_db_path_after_reset(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    p1 = str(tmp_path / "a.sqlite3")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", p1)
    reset_store_for_tests()
    s1 = get_store()
    assert getattr(s1, "_db_path", None) == p1

    # Change the path; without reset the stale singleton would keep p1.
    p2 = str(tmp_path / "b.sqlite3")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", p2)
    assert getattr(get_store(), "_db_path", None) == p1  # cached, unchanged

    reset_store_for_tests()
    s2 = get_store()
    assert getattr(s2, "_db_path", None) == p2
    assert s2 is not s1


def test_reset_clears_module_singleton(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "c.sqlite3"))
    reset_store_for_tests()
    get_store()
    assert store_module._store is not None
    reset_store_for_tests()
    assert store_module._store is None


def test_autouse_fixture_isolates_across_tests_part1(monkeypatch, tmp_path):
    # This test builds a store at a path unique to it; the autouse fixture must
    # ensure part2 does NOT see this store.
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "part1.sqlite3"))
    assert "part1.sqlite3" in getattr(get_store(), "_db_path", "")


def test_autouse_fixture_isolates_across_tests_part2(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "part2.sqlite3"))
    # If the autouse fixture failed to reset, this could still hold part1's store.
    assert "part2.sqlite3" in getattr(get_store(), "_db_path", "")


def test_production_import_and_get_store_still_work():
    # get_store() must remain usable with defaults (no crash on the production path).
    reset_store_for_tests()
    s = get_store()
    assert s is not None
    assert hasattr(s, "_db_path") or s.__class__.__name__ == "InMemoryStore"
