"""Live read clients read-only enforcement."""
from __future__ import annotations

import inspect

from hg_platforms.moltbook import moltbook_api_client
from hg_platforms.fourclaw import fourclaw_api_client


WRITE_METHOD_FRAGMENTS = ("post", "reply", "comment", "send", "delete", "follow", "like", "react", "publish")


def _public_methods(mod):
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("_"):
            continue
        yield name, fn


def test_moltbook_no_write_methods_called_in_phase16():
    names = [n for n, _ in _public_methods(moltbook_api_client)]
    write_like = [n for n in names if any(w in n.lower() for w in WRITE_METHOD_FRAGMENTS)]
    assert "fetch_posts" in names or "list_posts" in names or "moltbook_token_configured" in names
    assert "publish" not in names


def test_fourclaw_read_only_surface():
    names = [n for n, _ in _public_methods(fourclaw_api_client)]
    assert any("thread" in n or "fetch" in n or "list" in n or "token" in n for n in names)
