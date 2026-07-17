"""
Tests for Sticky Reality Ch1 ledger: canonical JSON, envelope, append, verify, emit.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.ledger import (
    append_event,
    build_envelope,
    emit,
    explain_message_provenance,
    explain_decision,
    compare_decisions,
    get_event,
    get_last_hash,
    iterate_events,
    verify_chain,
)
from hg_core.ledger.canonical_json import canonical_dumps
from hg_core.ledger.event_envelope import body_for_hash, compute_event_id, verify_envelope
from hg_core.ledger.ledger_writer import get_scope_ledger_path
from hg_core.scope_context import scope_context


SCOPE_RUN = {"type": "run", "id": "run_test_001"}
ACTOR = {"agent_id": "test-agent", "pubkey": "0" * 64, "key_id": "test"}


def test_canonical_dumps_stable():
    """Canonical encoding is deterministic (sorted keys)."""
    obj = {"z": 1, "a": 2, "m": []}
    a = canonical_dumps(obj)
    b = canonical_dumps(obj)
    assert a == b
    assert b.decode("utf-8").startswith('{"a"')


def test_event_id_recompute(tmp_path):
    """event_id is SHA-256 of canonical body."""
    envelope = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_1",
        payload={"reason": "test"},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    body = body_for_hash(envelope)
    computed = compute_event_id(body)
    assert envelope["event_id"] == computed
    assert len(computed) == 64
    assert all(c in "0123456789abcdef" for c in computed)


def test_verify_envelope_no_sig(tmp_path):
    """Verify passes when sig empty and event_id matches."""
    envelope = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_1",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
    )
    assert verify_envelope(envelope) is True


def test_append_and_iterate(tmp_path):
    """Append events to scope file and iterate."""
    e1 = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_1",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    e2 = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_2",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=e1["event_id"],
    )
    append_event(e1, tmp_path)
    append_event(e2, tmp_path)
    path = get_scope_ledger_path(tmp_path, "run", "run_test_001")
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    evs = list(iterate_events(tmp_path, scope_type="run", scope_id="run_test_001"))
    assert len(evs) == 2
    assert evs[0]["event_id"] == e1["event_id"]
    assert evs[1]["prev_hash"] == e1["event_id"]


def test_verify_chain(tmp_path):
    """verify_chain reports ok for valid chain."""
    e1 = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_1",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    append_event(e1, tmp_path)
    report = verify_chain(tmp_path, scope_type="run", scope_id="run_test_001")
    assert report["ok"] is True
    assert report["checked"] == 1


def test_emit_uses_scope_context(tmp_path):
    """emit() uses scope from scope_context when scope not passed."""
    with scope_context(scope_type="session", scope_id="sess_emit_test"):
        eid = emit(
            "ARTIFACT_PUBLISH",
            "artifact",
            "art_1",
            {"path": "x.yaml", "checksum": "sha256:abc"},
            workspace_root=tmp_path,
        )
    assert eid
    evs = list(iterate_events(tmp_path, scope_type="session", scope_id="sess_emit_test"))
    assert len(evs) == 1
    assert evs[0]["action"] == "ARTIFACT_PUBLISH"
    assert evs[0]["object"]["id"] == "art_1"


def test_get_event(tmp_path):
    """get_event returns event by event_id."""
    e1 = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_x",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    append_event(e1, tmp_path)
    found = get_event(tmp_path, e1["event_id"])
    assert found is not None
    assert found["event_id"] == e1["event_id"]
    assert get_event(tmp_path, "nonexistent") is None


def test_get_last_hash(tmp_path):
    """get_last_hash returns last event_id in scope."""
    assert get_last_hash(tmp_path, "run", "run_test_001") is None
    e1 = build_envelope(
        action="READ",
        object_type="entity",
        object_id="ent_1",
        payload={},
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    append_event(e1, tmp_path)
    assert get_last_hash(tmp_path, "run", "run_test_001") == e1["event_id"]


def test_explain_decision(tmp_path):
    """explain_decision returns claims, value_weights, context_ref for a decision."""
    payload = {
        "decision_id": "dec_abc",
        "title": "Throttle tool",
        "based_on_claim_ids": ["clm_1"],
        "value_weights": [{"dimension": "harm_reduction", "weight": 0.6}],
        "context_ref": {"retrieval_set_ids": ["ret_1"]},
        "produced_artifact_ids": ["art_1"],
    }
    ev = build_envelope(
        action="DECISION_COMMITTED",
        object_type="decision",
        object_id="dec_abc",
        payload=payload,
        scope=SCOPE_RUN,
        actor=ACTOR,
        prev_hash=None,
    )
    append_event(ev, tmp_path)
    out = explain_decision("dec_abc", tmp_path)
    assert out["decision_id"] == "dec_abc"
    assert out["based_on_claim_ids"] == ["clm_1"]
    assert out["value_weights"] == [{"dimension": "harm_reduction", "weight": 0.6}]
    assert out["produced_artifact_ids"] == ["art_1"]


def test_compare_decisions(tmp_path):
    """compare_decisions returns overlapping claims and value weight diffs."""
    for did, weights in [("dec_a", [{"dimension": "harm", "weight": 0.8}]), ("dec_b", [{"dimension": "harm", "weight": 0.3}])]:
        ev = build_envelope(
            action="DECISION_COMMITTED",
            object_type="decision",
            object_id=did,
            payload={"decision_id": did, "based_on_claim_ids": ["clm_x"], "value_weights": weights},
            scope=SCOPE_RUN,
            actor=ACTOR,
            prev_hash=None,
        )
        append_event(ev, tmp_path)
    out = compare_decisions("dec_a", "dec_b", tmp_path)
    assert "overlapping_claim_ids" in out
    assert "clm_x" in out["overlapping_claim_ids"]
    assert len(out["value_weight_diffs"]) >= 1
    assert out["value_weight_diffs"][0]["dimension"] == "harm"


def test_explain_message_provenance():
    """explain_message_provenance groups retrieval, policy, and evidence edges."""
    out = explain_message_provenance(
        message_id="msg_1",
        chat_id="chat_1",
        role="assistant",
        content="Here is the reply.",
        turn_provenance={
            "prompt_id": "prompt_default",
            "model_config_id": "model_default",
            "sampling_params": {"temperature": 0.2},
        },
        retrieval_sources=[{"title": "Doc", "url": "https://example.com", "snippet": "evidence"}],
        evidence_rows=[{"ledger_id": "led_1", "ts": "2026-03-23T00:00:00Z", "evidence_type": "support_claim"}],
        policy_notes=["assistant reply composed from prompt, model config, retrieval, and evidence ledger"],
    )
    assert out["message_id"] == "msg_1"
    assert out["chat_id"] == "chat_1"
    assert out["source_groups"]["retrieval"][0]["title"] == "Doc"
    assert out["source_groups"]["policy"][0]["kind"] == "prompt"
    assert out["source_groups"]["evidence"][0]["ledger_id"] == "led_1"
    assert "retrieval source" in out["why"]
