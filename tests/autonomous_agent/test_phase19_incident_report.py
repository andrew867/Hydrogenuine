"""Phase 19 incident report tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.action_ledger import Phase19Verdict
from hg_runtime.external_write_authority.incident_report import write_incident_report


def test_no_live_proof_incident_report_yellow(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.external_write_authority.incident_report.phase18_live_proof_status",
        lambda: {
            "live_proof_exists": False,
            "live_action_count": 0,
            "has_platform_url": False,
        },
    )
    monkeypatch.setattr(
        "hg_runtime.external_write_authority.incident_report.load_dispatch_rows",
        lambda: [],
    )
    monkeypatch.setattr(
        "hg_runtime.external_write_authority.incident_report.load_ledger_entries",
        lambda: [],
    )
    report = write_incident_report()
    assert report.verdict == Phase19Verdict.YELLOW_NO_PROOF
    assert report.phase18_live_proof_exists is False
    assert report.incident_type == "readiness_no_live_proof"


def test_incident_report_required_fields():
    report = write_incident_report()
    assert report.incident_report_id
    assert report.created_at
