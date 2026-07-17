from __future__ import annotations

import threading
from pathlib import Path

import pytest

from hg_core.consent.ledger import ConsentLedger


@pytest.fixture
def ledger(tmp_path: Path) -> ConsentLedger:
    return ConsentLedger(path=tmp_path / "consent_ledger.jsonl")


def test_grant_writes_consent_granted_row(ledger: ConsentLedger):
    row = ledger.grant(
        subject_id="user-1",
        consent_class="workspace",
        purpose="operator_panel",
        granted_by="op-admin",
    )
    assert row["event"] == "CONSENT_GRANTED"
    assert row["record_id"].startswith("cg_")
    assert row["subject_id"] == "user-1"
    assert row["consent_class"] == "workspace"
    assert ledger.read_all()[-1]["record_id"] == row["record_id"]


def test_revoke_appends_without_mutating_grant(ledger: ConsentLedger):
    grant = ledger.grant(
        subject_id="user-1",
        consent_class="workspace",
        purpose="test",
        granted_by="op",
    )
    revoke = ledger.revoke(record_id=grant["record_id"], subject_id="user-1", revoked_by="op")
    rows = ledger.read_all()
    assert rows[0]["event"] == "CONSENT_GRANTED"
    assert rows[0]["revoked_at"] is None
    assert rows[1]["event"] == "CONSENT_REVOKED"
    assert revoke["record_id"] == grant["record_id"]


def test_session_grant_requires_expiry(ledger: ConsentLedger):
    with pytest.raises(ValueError, match="expires_at"):
        ledger.grant(
            subject_id="user-1",
            consent_class="session",
            purpose="demo",
            granted_by="op",
        )


def test_concurrent_appends_preserve_lines(ledger: ConsentLedger):
    def _writer(i: int) -> None:
        ledger.deny_request(subject_id=f"u{i}", reason="probe")

    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rows = ledger.read_all()
    assert len(rows) == 20
    assert all(r["event"] == "CONSENT_DENIED_REQUEST" for r in rows)
