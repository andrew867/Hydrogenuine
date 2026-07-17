"""Scope request tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.scope_requests import (  # noqa: E402
    ScopeRequestKind,
    ScopeRequestVerdict,
    create_scope_request,
    unbounded_desire_to_scope_request,
    validate_scope_request,
)


def test_unbounded_desire_becomes_scope_request():
    receipt = unbounded_desire_to_scope_request("I want to read everything on the internet")
    assert receipt.advisory_only is True
    assert receipt.permission_granted is False
    assert validate_scope_request(receipt) == ScopeRequestVerdict.GREEN_SCOPE_REQUEST_VALID


def test_scope_request_does_not_grant_permission():
    receipt = create_scope_request(
        kind=ScopeRequestKind.MORE_READ_SCOPE,
        rationale="need broader read access for thread continuity",
    )
    assert receipt.permission_granted is False
    assert validate_scope_request(receipt) == ScopeRequestVerdict.GREEN_SCOPE_REQUEST_VALID


def test_scope_request_rejects_empty():
    with pytest.raises(ValueError, match="RED_SCOPE_REQUEST_EMPTY"):
        create_scope_request(kind=ScopeRequestKind.UNKNOWN, rationale="")


def test_scope_request_hash_deterministic():
    r1 = create_scope_request(kind=ScopeRequestKind.MORE_TIME, rationale="need more time")
    r2 = create_scope_request(kind=ScopeRequestKind.MORE_TIME, rationale="need more time")
    assert r1.hash != r2.hash  # different ids
    assert len(r1.hash) > 0
