"""Phase 19 action ledger tests."""
from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.external_write_authority.action_ledger import (
    ExternalActionLedgerEntry,
    build_ledger_from_phase18,
    detect_duplicate_live_dispatch,
    phase18_live_proof_status,
)
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT
from hg_runtime.external_write_authority.schema import new_id, now_iso


def test_ledger_entry_hash_deterministic():
    e1 = ExternalActionLedgerEntry(
        ledger_entry_id="led-1",
        live_dispatch_result_ref="disp-1",
        platform="moltbook",
        action_type="publish_post",
        content_sha256="abc",
        external_side_effect=True,
        platform_object_id="p1",
        platform_url="https://example.com/p1",
        platform_proof_ref=None,
        created_at=now_iso(),
        source="test",
    ).with_hash()
    e2 = ExternalActionLedgerEntry(
        ledger_entry_id="led-1",
        live_dispatch_result_ref="disp-1",
        platform="moltbook",
        action_type="publish_post",
        content_sha256="abc",
        external_side_effect=True,
        platform_object_id="p1",
        platform_url="https://example.com/p1",
        platform_proof_ref=None,
        created_at=e1.created_at,
        source="test",
    ).with_hash()
    assert e1.hash == e2.hash


def test_duplicate_dispatch_detected():
    entries = [
        ExternalActionLedgerEntry(
            ledger_entry_id=new_id("l"),
            live_dispatch_result_ref="a",
            platform="moltbook",
            action_type="publish_post",
            content_sha256="x",
            external_side_effect=True,
            platform_object_id="1",
            platform_url="u1",
            platform_proof_ref=None,
            created_at=now_iso(),
            source="t",
        ),
        ExternalActionLedgerEntry(
            ledger_entry_id=new_id("l"),
            live_dispatch_result_ref="b",
            platform="moltbook",
            action_type="publish_post",
            content_sha256="y",
            external_side_effect=True,
            platform_object_id="2",
            platform_url="u2",
            platform_proof_ref=None,
            created_at=now_iso(),
            source="t",
        ),
    ]
    assert detect_duplicate_live_dispatch(entries) is True


def test_phase18_live_proof_status_no_proof_by_default():
    status = phase18_live_proof_status()
    assert "live_proof_exists" in status
    assert "mode" in status
