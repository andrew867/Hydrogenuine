"""Tests for per-task posting dedupe: no double post on retry (plan a1)."""

import pytest
from pathlib import Path

from hg_core.posting_dedupe import (
    check_already_posted,
    record_posted,
    get_date_bucket,
    make_dedupe_key,
)


def test_make_dedupe_key():
    assert make_dedupe_key("fourclaw-auto-post", "2026-02-23", "abc123") == "fourclaw-auto-post:2026-02-23:abc123"


def test_get_date_bucket():
    b = get_date_bucket()
    assert len(b) == 10 and b[4] == "-" and b[7] == "-"


def test_check_already_posted_empty(tmp_path):
    assert check_already_posted(
        tmp_path, "automation-fourclaw-auto-post", "fourclaw-auto-post",
        "2026-02-23", "hash1",
    ) is None


def test_record_and_check_already_posted(tmp_path):
    session = "automation-fourclaw-auto-post"
    task_id = "fourclaw-auto-post"
    date_bucket = "2026-02-23"
    content_hash = "abc123"
    record_posted(
        tmp_path, session, task_id, date_bucket, content_hash,
        thread_id="t1", thread_url="https://example.com/t/t1",
    )
    out = check_already_posted(tmp_path, session, task_id, date_bucket, content_hash)
    assert out is not None
    assert out.get("thread_id") == "t1"
    assert out.get("thread_url") == "https://example.com/t/t1"


def test_different_content_hash_not_dedupe(tmp_path):
    session = "automation-fourclaw-auto-post"
    task_id = "fourclaw-auto-post"
    date_bucket = "2026-02-23"
    record_posted(tmp_path, session, task_id, date_bucket, "hash1", thread_id="t1", thread_url="https://x.com/t1")
    assert check_already_posted(tmp_path, session, task_id, date_bucket, "hash2") is None
    assert check_already_posted(tmp_path, session, task_id, date_bucket, "hash1") is not None


def test_idempotent_retry_returns_same_result_no_second_post(tmp_path):
    """Second 'post' with same (task, date, content) must return stored result; no second API call."""
    session = "automation-fourclaw-auto-post"
    task_id = "fourclaw-auto-post"
    date_bucket = "2026-02-23"
    content_hash = "samecontent"
    record_posted(
        tmp_path, session, task_id, date_bucket, content_hash,
        thread_id="thread-42", thread_url="https://www.4claw.org/t/thread-42",
    )
    # Simulate retry: check_already_posted must return the stored result so caller does not post again.
    result = check_already_posted(tmp_path, session, task_id, date_bucket, content_hash)
    assert result is not None
    assert result["thread_id"] == "thread-42"
    assert result["thread_url"] == "https://www.4claw.org/t/thread-42"
    # If the real post path uses this result and returns it with idempotent=True, no double post occurs.
    # A test that actually runs create_thread_async twice would mock the client and assert create_thread call count == 1;
    # this unit test enforces the contract that check_already_posted returns the stored result for the same key.
    assert result.get("at")
