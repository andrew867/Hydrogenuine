"""Lifecycle anchor audit tests."""

from __future__ import annotations

from hg_runtime.extended_dry_autonomy.anchor_audit import audit_lifecycle_anchors


def test_local_boot_anchor_required():
    audit = audit_lifecycle_anchors(run_id="r", boot_anchor=None)
    assert audit.verdict == "RED_BOOT_ANCHOR_MISSING"


def test_local_clean_stop_required():
    audit = audit_lifecycle_anchors(
        run_id="r",
        boot_anchor={"local_committed": True, "journal_receipt_id": "boot"},
        shutdown_anchor=None,
    )
    assert audit.verdict == "RED_SHUTDOWN_ANCHOR_MISSING"


def test_panic_anchor_required_on_panic():
    audit = audit_lifecycle_anchors(
        run_id="r",
        boot_anchor={"local_committed": True, "journal_receipt_id": "boot"},
        panic_anchor=None,
        shutdown_anchor=None,
    )
    assert audit.verdict == "RED_SHUTDOWN_ANCHOR_MISSING"


def test_local_only_returns_yellow():
    audit = audit_lifecycle_anchors(
        run_id="r",
        boot_anchor={"local_committed": True, "journal_receipt_id": "boot"},
        shutdown_anchor={"local_committed": True, "journal_receipt_id": "stop"},
        remote_anchor_push_allowed=False,
    )
    assert audit.verdict == "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"


def test_remote_disabled_not_green_remote(monkeypatch):
    monkeypatch.setenv("HG_ANCHOR_ALLOW_PUSH", "false")
    audit = audit_lifecycle_anchors(
        run_id="r",
        boot_anchor={"local_committed": True, "journal_receipt_id": "boot", "pushed": False},
        shutdown_anchor={"local_committed": True, "journal_receipt_id": "stop"},
        remote_anchor_push_allowed=True,
    )
    assert audit.verdict != "GREEN_REMOTE_ANCHOR_FRESH"


def test_clean_stop_committed():
    audit = audit_lifecycle_anchors(
        run_id="r",
        boot_anchor={"local_committed": True, "journal_receipt_id": "boot"},
        shutdown_anchor={"local_committed": True, "journal_receipt_id": "stop"},
    )
    assert audit.boot_anchor_ref == "boot"
    assert audit.shutdown_anchor_ref == "stop"
