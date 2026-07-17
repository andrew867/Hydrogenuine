"""EXCITON Phase 0 — end-to-end snapshot + safety invariants."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.exciton import (
    ExcitonControlBoundary,
    ExcitonControlKind,
    ExcitonControlRequest,
    build_snapshot,
)
from hg_runtime.exciton.agent0_context import build_exciton_agent0_context
from hg_runtime.exciton.operator_notes import make_note
from hg_runtime.exciton.receipts import control_receipt, snapshot_receipt
from hg_runtime.exciton.schema import new_id
from hg_runtime.exciton.panel_registry import (
    AGENT_ZERO_CONSOLE_REQUIRED_PANELS,
    INFERENCE_WATCHTOWER_REQUIRED_PANELS,
    PHASE_1_REQUIRED_PANELS,
    PHASE_2_REQUIRED_PANELS,
    PHASE_3_REQUIRED_PANELS,
    REQUIRED_PANELS,
    SITUATIONAL_REQUIRED_PANELS,
)
from hg_runtime.exciton.status_aggregator import AggregatorConfig


def test_end_to_end_snapshot_is_safe():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    p = snap.to_payload()
    assert p["overall_verdict"].startswith(("GREEN", "YELLOW"))  # never fake-green; not RED here
    assert p["advisory_only"] is True
    assert p["permission_granted"] is False
    assert p["authority_created"] is False
    assert p["dangerous_actions_disabled"] is True
    assert p["stop_available"] is True and p["panic_available"] is True
    panel_ids = [x["panel_id"] for x in p["panels"]]
    # Contract migration M4: snapshot spans base + phase panels + situational + inference + console.
    assert len(panel_ids) == (
        len(REQUIRED_PANELS) + len(PHASE_1_REQUIRED_PANELS)
        + len(PHASE_2_REQUIRED_PANELS) + len(PHASE_3_REQUIRED_PANELS)
        + len(SITUATIONAL_REQUIRED_PANELS) + len(INFERENCE_WATCHTOWER_REQUIRED_PANELS)
        + len(AGENT_ZERO_CONSOLE_REQUIRED_PANELS)
    )
    assert all(pid in panel_ids for pid in SITUATIONAL_REQUIRED_PANELS)
    assert all(pid in panel_ids for pid in REQUIRED_PANELS)
    assert all(pid in panel_ids for pid in PHASE_1_REQUIRED_PANELS)
    assert all(pid in panel_ids for pid in PHASE_3_REQUIRED_PANELS)
    assert all(pid in panel_ids for pid in AGENT_ZERO_CONSOLE_REQUIRED_PANELS)


def test_snapshot_receipt_is_evidence_not_authority():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    rcpt = snapshot_receipt(snap).to_payload()
    assert rcpt["kind"] == "snapshot"
    assert rcpt["permission_granted"] is False
    assert rcpt["authority_created"] is False
    assert rcpt["ref_hash"].startswith("sha256:")


def test_control_receipt_records_routing():
    boundary = ExcitonControlBoundary()
    decision = boundary.decide(ExcitonControlRequest(new_id("req"), ExcitonControlKind.PANIC_STOP))
    rcpt = control_receipt(decision, datetime.now(timezone.utc).isoformat()).to_payload()
    assert rcpt["detail"]["decision"] == "FULL_STOP"
    assert rcpt["permission_granted"] is False


def test_operator_note_is_draft_not_consent():
    note = make_note("remember to review anchor queue", datetime.now(timezone.utc).isoformat())
    p = note.to_payload()
    assert p["is_instruction"] is False
    assert p["is_consent"] is False
    assert p["permission_granted"] is False


def test_agent0_context_is_status_surface_not_authority():
    ctx = build_exciton_agent0_context(offline_fixture=True).to_payload()
    assert ctx["is_status_surface"] is True
    assert ctx["is_authority"] is False
    assert ctx["permission_granted"] is False
    assert ctx["authority_created"] is False
    assert "throne" in ctx["instruction"].lower()
    assert ctx["temporal"]  # carries Agent Zero time


def test_no_live_side_effect_control_exists():
    # The boundary maps every forbidden action to DENY — no executor is reachable.
    boundary = ExcitonControlBoundary()
    for kind in (ExcitonControlKind.SEND_EMAIL, ExcitonControlKind.PUBLISH_SOCIAL,
                 ExcitonControlKind.START_SOAK, ExcitonControlKind.START_OEA):
        assert boundary.decide(ExcitonControlRequest(new_id("r"), kind)).decision.value == "DENY"
