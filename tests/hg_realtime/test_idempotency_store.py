"""Idempotency store: get/set, TTL expiry."""

import os
import tempfile
import time

import pytest

from hg_realtime.integrations.idempotency_store import SqliteIdempotencyStore


def test_idempotency_same_key_twice_returns_cached():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        store = SqliteIdempotencyStore(db_path=path)
        store.set("key12345678", {"ok": True, "data": 1}, ttl_seconds=60)
        got = store.get("key12345678")
        assert got == {"ok": True, "data": 1}
        got2 = store.get("key12345678")
        assert got2 == {"ok": True, "data": 1}
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass


def test_idempotency_ttl_expiry_returns_miss():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        store = SqliteIdempotencyStore(db_path=path)
        store.set("key-ttl-expiry-123", {"ok": True}, ttl_seconds=0)
        time.sleep(0.02)
        got = store.get("key-ttl-expiry-123")
        assert got is None
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass


def test_idempotency_missing_key_returns_none():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        store = SqliteIdempotencyStore(db_path=path)
        assert store.get("nonexistent-key-12345") is None
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass
