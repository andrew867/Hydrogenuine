from __future__ import annotations

import json
from pathlib import Path

from hg_gateway.db_hardening import verify_gateway_hardening


def test_gateway_hardening_probe_reports_indexes_and_unicode(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    summary = verify_gateway_hardening()

    assert summary["all_passed"] is True
    checks = {item["check"]: item for item in summary["checks"]}
    assert checks["schema_version_current"]["passed"] is True
    assert checks["required_indexes_present"]["passed"] is True
    assert checks["unicode_roundtrip"]["passed"] is True
    assert checks["repeatable_bootstrap"]["passed"] is True

