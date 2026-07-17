"""CT-05 incident lifecycle tests."""

from __future__ import annotations

import pytest

from hg_core.failures.incident import IncidentLedger
from hg_core.failures.registry import clear_registry_cache


@pytest.fixture(autouse=True)
def _reset() -> None:
    clear_registry_cache()


def test_ftx_i2_incident_lifecycle() -> None:
    ledger = IncidentLedger()
    incident = ledger.open_incident("rtc.chain_broken.event_log")
    ledger.attach(incident.incident_id, "ter.refused.jail_violation")
    export = ledger.export_bundle(incident.incident_id)
    assert export["schema"] == "ftx_incident_export_v1"
    assert len(export["incident"]["attached_codes"]) == 2
    closed = ledger.close(incident.incident_id, operator_id="op:local")
    assert closed.closed_by == "op:local"


def test_incident_close_requires_audit_scope() -> None:
    ledger = IncidentLedger()
    incident = ledger.open_incident("rtc.chain_broken.event_log")
    with pytest.raises(ValueError):
        ledger.close(incident.incident_id, operator_id="op:forged")
