"""AnchorWriter policy tests."""

from __future__ import annotations

import pytest

import shutil

from hg_runtime.external_witness_journal.anchor_writer import append_journal_event
from hg_runtime.external_witness_journal.schema import (
    AnchorWriterRequest,
    AnchorWriterRequestKind,
    WitnessAppendDecision,
    WitnessEventClass,
    WitnessImportanceClass,
    WitnessJournalConfig,
)

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


def test_anchor_writer_denies_agent_live_push():
    cfg = WitnessJournalConfig()
    req = AnchorWriterRequest(
        kind=AnchorWriterRequestKind.ANCHOR_IMPORTANT_EVENT,
        event_class=WitnessEventClass.IMPORTANT_STATE_MARKER,
        importance=WitnessImportanceClass.IMPORTANT,
        summary="agent wants anchor",
        agent_requested=True,
        push_requested=True,
    )
    result = append_journal_event(cfg, req, dry_run=False, push=True)
    assert result.decision.decision == WitnessAppendDecision.DENY
    assert "UNAPPROVED" in result.decision.verdict or result.decision.verdict.startswith("RED")


def test_anchor_writer_queues_important_marker():
    cfg = WitnessJournalConfig()
    req = AnchorWriterRequest(
        kind=AnchorWriterRequestKind.ANCHOR_IMPORTANT_EVENT,
        event_class=WitnessEventClass.IMPORTANT_STATE_MARKER,
        importance=WitnessImportanceClass.IMPORTANT,
        summary="important state",
        agent_requested=True,
        push_requested=False,
    )
    result = append_journal_event(cfg, req, dry_run=True)
    assert result.decision.decision == WitnessAppendDecision.QUEUE_FOR_OPERATOR
    assert result.receipt is not None
    assert result.receipt.queue_path


def test_operator_pinned_allowed_local(tmp_path):
    cfg = WitnessJournalConfig()
    req = AnchorWriterRequest(
        kind=AnchorWriterRequestKind.OPERATOR_APPEND,
        event_class=WitnessEventClass.OPERATOR_MARKER,
        importance=WitnessImportanceClass.OPERATOR_PINNED,
        summary="operator pin",
        operator_invoked=True,
        push_requested=False,
    )
    result = append_journal_event(cfg, req, dry_run=True, workspace=tmp_path)
    assert result.bundle is not None
    assert result.decision.decision == WitnessAppendDecision.ALLOW_LOCAL_ONLY


@_requires_gh
def test_lifecycle_mission_events(tmp_path):
    from hg_runtime.external_witness_journal.lifecycle import append_first_wake_start

    r = append_first_wake_start(dry_run=True, workspace=tmp_path, operator_invoked=True)
    assert r.bundle is not None
    assert r.bundle.event_class == WitnessEventClass.FIRST_WAKE_START
