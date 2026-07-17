from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hg_core.consent.ledger import ConsentLedger
from hg_core.consent.resolver import resolve_consent_class


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def ledger(workspace: Path) -> ConsentLedger:
    return ConsentLedger(path=workspace / "memory" / "governance" / "consent_ledger.jsonl")


def test_no_records_returns_none(workspace: Path):
    assert resolve_consent_class("user-1", workspace_root=workspace) == "none"


def test_active_workspace_grant(ledger: ConsentLedger, workspace: Path):
    ledger.grant(
        subject_id="user-1",
        consent_class="workspace",
        purpose="panel",
        granted_by="op",
    )
    assert resolve_consent_class("user-1", workspace_root=workspace) == "workspace"


def test_expired_session_grant_returns_none_and_writes_expire(ledger: ConsentLedger, workspace: Path):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    ledger.grant(
        subject_id="user-1",
        consent_class="session",
        purpose="demo",
        granted_by="op",
        expires_at=past,
    )
    assert resolve_consent_class("user-1", workspace_root=workspace) == "none"
    events = [r["event"] for r in ledger.read_all()]
    assert "CONSENT_EXPIRED" in events


def test_revoked_grant_returns_none(ledger: ConsentLedger, workspace: Path):
    grant = ledger.grant(
        subject_id="user-1",
        consent_class="research",
        purpose="study",
        granted_by="op",
    )
    ledger.revoke(record_id=grant["record_id"], subject_id="user-1", revoked_by="op")
    assert resolve_consent_class("user-1", workspace_root=workspace) == "none"


def test_multiple_classes_returns_highest_active(ledger: ConsentLedger, workspace: Path):
    ledger.grant(subject_id="user-1", consent_class="session", purpose="a", granted_by="op", expires_at="2099-01-01T00:00:00Z")
    ledger.grant(subject_id="user-1", consent_class="workspace", purpose="b", granted_by="op")
    assert resolve_consent_class("user-1", workspace_root=workspace) == "workspace"


def test_resolver_exception_path_fail_closed(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr("hg_core.consent.resolver._ledger_for", _boom)
    assert resolve_consent_class("user-1") == "none"
