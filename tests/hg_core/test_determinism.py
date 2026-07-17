"""Tests for determinism envelope: seed from (task_id, date) (plan a2)."""

import pytest
from hg_core.determinism import get_run_seed, get_date_bucket


def test_same_task_and_date_same_seed():
    assert get_run_seed("fourclaw-auto-post", "2026-02-23") == get_run_seed("fourclaw-auto-post", "2026-02-23")


def test_different_date_different_seed():
    s1 = get_run_seed("fourclaw-auto-post", "2026-02-23")
    s2 = get_run_seed("fourclaw-auto-post", "2026-02-24")
    assert s1 != s2


def test_different_task_different_seed():
    s1 = get_run_seed("fourclaw-auto-post", "2026-02-23")
    s2 = get_run_seed("moltbook-auto-post", "2026-02-23")
    assert s1 != s2


def test_seed_is_int():
    assert isinstance(get_run_seed("x", "2026-02-23"), int)


def test_get_date_bucket_format():
    b = get_date_bucket()
    assert len(b) == 10
    assert b[4] == "-" and b[7] == "-"
