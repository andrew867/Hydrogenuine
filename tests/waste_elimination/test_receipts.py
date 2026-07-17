"""Waste elimination receipt tests."""

from __future__ import annotations

from hg_runtime.wake_refresh.receipts import new_waste_receipt
from hg_runtime.wake_refresh.schema import WasteClass


def test_waste_receipt_frozen():
    r = new_waste_receipt(".hg-local/tmp/x", WasteClass.TEMP_FILE, "stale")
    p = r.to_payload()
    assert p["permission_granted"] is False
    assert p["authority_created"] is False
    assert p["receipt_id"].startswith("wer-")


def test_no_secret_in_receipt():
    r = new_waste_receipt(".hg-local/tmp/file", WasteClass.TEMP_FILE, "cleanup", content_hash="abc")
    assert "sk-" not in r.to_payload()["reason"]
