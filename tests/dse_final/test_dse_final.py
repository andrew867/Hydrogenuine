"""DSE-FINAL integration tests."""

from __future__ import annotations

from hg_core.dse.final_registry import DSE_GATES, run_dse_final_checks


def test_dse_gate_registry_complete() -> None:
    assert len(DSE_GATES) == 11


def test_dse_final_checks_green() -> None:
    result = run_dse_final_checks()
    assert result["ok"] is True
