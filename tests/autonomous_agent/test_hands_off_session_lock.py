"""Session lock overlap prevention."""
from __future__ import annotations

import pytest

from hg_runtime.hands_off_session.errors import HandsOffLockError
from hg_runtime.hands_off_session.session_lock import acquire_lock, read_lock, release_lock


@pytest.fixture
def lock_root(tmp_path, monkeypatch):
    root = tmp_path / "hands_off"
    monkeypatch.setattr("hg_runtime.hands_off_session.schema.STORE_ROOT", root)
    monkeypatch.setattr("hg_runtime.hands_off_session.session_lock.STORE_ROOT", root)
    return root


def test_lock_prevents_overlap(lock_root):
    acquire_lock("sess-a", base=lock_root)
    with pytest.raises(HandsOffLockError):
        acquire_lock("sess-b", base=lock_root)
    release_lock("sess-a", base=lock_root)


def test_lock_released(lock_root):
    acquire_lock("sess1", base=lock_root)
    release_lock("sess1", base=lock_root)
    lock = read_lock(base=lock_root)
    assert lock is None or lock.state.value == "released"
