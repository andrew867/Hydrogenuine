"""
Ch5 Social awareness: handoffs, availability, belief model, escalation, conflict, misalignment detection.
See .cursor/plans/stickyreality/chapter5/social_awareness_theory_of_mind/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.social import (
    create_handoff,
    accept_handoff,
    reject_handoff,
    complete_handoff,
    declare_availability,
    record_belief_model_updated,
    record_belief_override,
    raise_escalation,
    record_conflict,
    detect_misalignments,
    list_handoffs,
    list_availability,
    list_beliefs,
    list_exposures,
    list_escalations,
    list_conflicts,
    list_misalignments,
)
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers.decision_materializer import run as run_decision_materializer
from hg_core.materializers.social_indexer import run as run_social_indexer


SCOPE = {"type": "run", "id": "test_run"}
ACTOR = {"agent_id": "agent_A", "pubkey": "0" * 64, "key_id": "k"}


def test_handoff_created_emits_and_has_notes_artifact(tmp_path: Path):
    """create_handoff emits HANDOFF_CREATED and writes notes artifact when notes provided."""
    hid = create_handoff(
        from_agent_id="A",
        to_agent_id="B",
        work_item_ref={"type": "decision", "id": "dec_1"},
        ownership_mode="delegate",
        expected_response_by="2026-12-31T23:59:59Z",
        priority="high",
        scope=SCOPE,
        actor=ACTOR,
        notes="Please review",
        workspace_root=tmp_path,
    )
    assert hid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "HANDOFF_CREATED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "HANDOFF_CREATED")
    assert payload["from_agent_id"] == "A"
    assert payload["to_agent_id"] == "B"
    assert payload["ownership_mode"] == "delegate"
    assert (tmp_path / "artifacts" / "social" / "handoffs").exists()


def test_handoff_accept_reject_complete(tmp_path: Path):
    """accept_handoff, reject_handoff, complete_handoff emit corresponding events."""
    hid = create_handoff(
        from_agent_id="A", to_agent_id="B",
        work_item_ref={"type": "task", "id": "t1"},
        ownership_mode="own",
        expected_response_by="2026-12-31Z",
        priority="normal",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    accept_handoff(hid, scope=SCOPE, actor={**ACTOR, "agent_id": "B"}, workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "HANDOFF_ACCEPTED" for _, _, ev in evs)
    reject_handoff("other_id", reason="busy", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    complete_handoff(hid, outcome={"done": True}, scope=SCOPE, actor={**ACTOR, "agent_id": "B"}, workspace_root=tmp_path)
    evs2 = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "HANDOFF_REJECTED" for _, _, ev in evs2)
    assert any(ev.get("action") == "HANDOFF_COMPLETED" for _, _, ev in evs2)


def test_declare_availability_emits(tmp_path: Path):
    """declare_availability emits AVAILABILITY_DECLARED with windows and rationale ref."""
    rec_id = declare_availability(
        agent_id="agent_B",
        windows=[{"start_ts": "2026-02-24T18:00:00Z", "end_ts": "2026-02-24T23:00:00Z", "status": "available"}],
        timezone="UTC",
        scope=SCOPE,
        actor=ACTOR,
        notes="On-call",
        workspace_root=tmp_path,
    )
    assert rec_id
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "AVAILABILITY_DECLARED" for _, _, ev in evs)


def test_belief_model_updated_requires_basis_refs(tmp_path: Path):
    """record_belief_model_updated requires basis_refs; emits BELIEF_MODEL_UPDATED."""
    with pytest.raises(ValueError, match="basis_refs"):
        record_belief_model_updated(
            subject_agent_id="A",
            scope=SCOPE,
            confidence=0.8,
            basis_refs=[],
            actor=ACTOR,
            workspace_root=tmp_path,
        )
    bid = record_belief_model_updated(
        subject_agent_id="A",
        scope=SCOPE,
        confidence=0.8,
        basis_refs=[{"type": "retrieval_set", "id": "rs1"}],
        claim_id="claim_1",
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert bid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "BELIEF_MODEL_UPDATED" for _, _, ev in evs)


def test_belief_override_emits_with_rationale(tmp_path: Path):
    """record_belief_override emits BELIEF_MODEL_OVERRIDDEN with rationale artifact; never mutates facts."""
    eid = record_belief_override(
        subject_agent_id="A",
        scope=SCOPE,
        claim_id="c1",
        rationale="Operator correction per ticket",
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert eid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "BELIEF_MODEL_OVERRIDDEN" for _, _, ev in evs)


def test_escalation_and_conflict(tmp_path: Path):
    """raise_escalation and record_conflict emit ESCALATION_RAISED and CONFLICT_DETECTED."""
    raise_escalation(reason="missed_deadline", handoff_id="h1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_conflict(
        work_item_ref={"type": "decision", "id": "d1"},
        agent_ids=["A", "B"],
        trace=[{"event": "handoff"}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "ESCALATION_RAISED" for _, _, ev in evs)
    assert any(ev.get("action") == "CONFLICT_DETECTED" for _, _, ev in evs)


def test_misalignment_detector_triggers_on_unexposed_claim(tmp_path: Path):
    """When decision cites claim_id not in exposure graph, detect_misalignments emits MISALIGNMENT_DETECTED."""
    emit(
        "RETRIEVAL_SET",
        "retrieval_set", "rs1",
        {"top_k_ids": ["claim_X"], "selected_ids": []},
        scope=SCOPE, actor={**ACTOR, "agent_id": "agent_A"}, workspace_root=tmp_path,
    )
    emit(
        "DECISION_COMMITTED",
        "decision", "dec_m",
        {"decision_id": "dec_m", "title": "D", "based_on_claim_ids": ["claim_X", "claim_Y"], "value_weights": [], "context_ref": {}, "produced_artifact_ids": []},
        scope=SCOPE, actor={**ACTOR, "agent_id": "agent_A"}, workspace_root=tmp_path,
    )
    run_decision_materializer(tmp_path, rebuild=True)
    run_social_indexer(tmp_path, rebuild=True)
    emitted = detect_misalignments(tmp_path, scope=SCOPE, actor=ACTOR)
    assert len(emitted) >= 1
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "MISALIGNMENT_DETECTED" for _, _, ev in evs)


def test_social_indexer_and_api(tmp_path: Path):
    """Social indexer produces handoffs/exposures/beliefs; API lists them."""
    create_handoff(
        from_agent_id="A", to_agent_id="B",
        work_item_ref={"type": "task", "id": "t1"},
        ownership_mode="delegate",
        expected_response_by="2026-12-31Z",
        priority="normal",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    run_social_indexer(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "handoffs.jsonl").exists()
    assert (root / "exposures.jsonl").exists()
    handoffs = list_handoffs(tmp_path, scope_id="test_run")
    assert len(handoffs) >= 1
    assert handoffs[0].get("from_agent_id") == "A"
