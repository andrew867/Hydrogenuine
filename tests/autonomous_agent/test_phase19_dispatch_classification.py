"""Phase 19 dispatch classification and ledger pollution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.external_write_authority.dispatch_classification import (
    DISPATCH_DEBUG_UNAUTHORIZED,
    DISPATCH_DRY_RUN,
    DISPATCH_ENVELOPE_AUTHORIZED,
    analyze_ledger_pollution,
    classify_dispatch_result,
    phase19_verdict_for_pollution,
)


def _registry() -> dict:
    return {
        "envelope_authorized_platform_object_ids": ["auth-post-1"],
        "envelope_authorized_dispatch_result_ids": ["p18-live-dispatch-auth"],
        "debug_platform_object_ids": ["debug-post-1"],
        "incident_report_doc": "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_REAL_SOAK_DEBUG_DISPATCH_INCIDENT_20260618.md",
        "operator_run_report_doc": "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_REAL_SOAK_OPERATOR_RUN_20260618_REPORT.md",
    }


def test_classify_envelope_authorized_by_object_id():
    row = {"external_side_effect": True, "platform_object_id": "auth-post-1"}
    assert classify_dispatch_result(row, registry=_registry()) == DISPATCH_ENVELOPE_AUTHORIZED


def test_classify_debug_unauthorized_by_object_id():
    row = {"external_side_effect": True, "platform_object_id": "debug-post-1"}
    assert classify_dispatch_result(row, registry=_registry()) == DISPATCH_DEBUG_UNAUTHORIZED


def test_classify_real_soak_scope_as_envelope_authorized():
    row = {"external_side_effect": True, "scope": "real_soak:tonight:general:single"}
    assert classify_dispatch_result(row) == DISPATCH_ENVELOPE_AUTHORIZED


def test_dry_run_not_envelope_authorized():
    row = {"external_side_effect": False, "scope": "real_soak:tonight:general:single"}
    assert classify_dispatch_result(row) == DISPATCH_DRY_RUN


def test_duplicate_live_dispatch_detected_in_pollution():
    rows = [
        {"external_side_effect": True, "platform_object_id": "auth-post-1"},
        {"external_side_effect": True, "platform_object_id": "debug-post-1"},
    ]
    analysis = analyze_ledger_pollution(rows, registry=_registry())
    assert analysis.duplicate_live_dispatch_detected is True
    assert analysis.envelope_authorized_live_count == 1
    assert analysis.debug_unauthorized_live_count == 1


def test_yellow_verdict_when_pollution_acknowledged():
    workspace = Path(__file__).resolve().parents[2]
    incident_doc = workspace / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_REAL_SOAK_DEBUG_DISPATCH_INCIDENT_20260618.md"
    operator_doc = workspace / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_REAL_SOAK_OPERATOR_RUN_20260618_REPORT.md"
    if not incident_doc.is_file() or not operator_doc.is_file():
        pytest.skip("incident closure reports not yet present")

    rows = [
        {"external_side_effect": True, "platform_object_id": "auth-post-1"},
        {"external_side_effect": True, "platform_object_id": "debug-post-1"},
    ]
    analysis = analyze_ledger_pollution(rows, registry=_registry())
    verdict = phase19_verdict_for_pollution(analysis)
    assert verdict == "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"


def test_red_verdict_when_duplicate_envelope_posts():
    rows = [
        {"external_side_effect": True, "platform_object_id": "auth-post-1", "scope": "real_soak:a:b:single"},
        {"external_side_effect": True, "platform_object_id": "auth-post-2", "scope": "real_soak:a:b:single"},
    ]
    analysis = analyze_ledger_pollution(rows, registry=_registry())
    assert analysis.duplicate_envelope_authorized_detected is True
    assert phase19_verdict_for_pollution(analysis) == "RED_DUPLICATE_LIVE_DISPATCH_DETECTED"


def test_same_object_readback_idempotent_classification():
    rows = [
        {
            "external_side_effect": True,
            "platform_object_id": "auth-post-1",
            "live_dispatch_result_id": "p18-live-dispatch-auth",
        },
        {
            "external_side_effect": True,
            "platform_object_id": "auth-post-1",
            "live_dispatch_result_id": "p18-live-dispatch-readback",
        },
    ]
    analysis = analyze_ledger_pollution(rows, registry=_registry())
    assert analysis.envelope_authorized_live_count == 1
    assert analysis.duplicate_envelope_authorized_detected is False


def test_debug_dispatch_cannot_count_as_envelope_success():
    rows = [{"external_side_effect": True, "platform_object_id": "debug-post-1"}]
    analysis = analyze_ledger_pollution(rows, registry=_registry())
    assert analysis.envelope_authorized_live_count == 0
    assert analysis.debug_unauthorized_live_count == 1
