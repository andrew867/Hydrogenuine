"""Tests for Sticky Reality Ch1 materializers."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.ledger import build_envelope, append_event
from hg_core.ledger.ledger_writer import get_scope_ledger_path
from hg_core.materializers import run_all
from hg_core.materializers.molecules_materializer import run as run_molecules
from hg_core.materializers.decision_materializer import run as run_decision
from hg_core.materializers.reputation_materializer import run as run_reputation
from hg_core.materializers._checkpoint import get_materialized_root, load_checkpoint

SCOPE = {"type": "run", "id": "run_mat"}
ACTOR = {"agent_id": "agent1", "pubkey": "0" * 64, "key_id": "k1"}


def test_molecules_materializer_produces_files(tmp_path):
    """Molecules materializer writes molecules.jsonl and molecules_edges.jsonl."""
    prev = None
    for i in range(3):
        ev = build_envelope("READ", "entity", f"ent_{i}", {}, SCOPE, ACTOR, prev_hash=prev)
        prev = ev["event_id"]
        append_event(ev, tmp_path)
    run_molecules(tmp_path, rebuild=False)
    root = get_materialized_root(tmp_path)
    assert (root / "molecules.jsonl").exists()
    lines = (root / "molecules.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    rec = json.loads(lines[0])
    assert rec["agent_id"] == "agent1"
    assert "selected_ids" in rec or "count" in rec


def test_decision_materializer_produces_decisions(tmp_path):
    """Decision materializer writes decisions.jsonl from DECISION_COMMITTED."""
    ev = build_envelope(
        "DECISION_COMMITTED",
        "decision",
        "dec_1",
        {"decision_id": "dec_1", "title": "Test", "value_weights": [{"dimension": "x", "weight": 0.5}]},
        SCOPE,
        ACTOR,
        prev_hash=None,
    )
    append_event(ev, tmp_path)
    run_decision(tmp_path, rebuild=False)
    root = get_materialized_root(tmp_path)
    assert (root / "decisions.jsonl").exists()
    lines = (root / "decisions.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["decision_id"] == "dec_1"
    assert rec["title"] == "Test"


def test_run_all(tmp_path):
    """run_all creates materialized dir and runs all materializers (incl. observations index)."""
    run_all(tmp_path, rebuild=False)
    root = get_materialized_root(tmp_path)
    assert (root / "molecules.jsonl").exists()
    assert (root / "decisions.jsonl").exists()
    assert (root / "reputation_timeseries.jsonl").exists()
    assert (root / "observations.jsonl").exists()
    assert (root / "self_assessments.jsonl").exists()
    assert (root / "tool_reliability.jsonl").exists()
    assert (root / "calibration_curve.jsonl").exists()
    assert (root / "episodes.jsonl").exists()
    assert (root / "timeline.jsonl").exists()
    assert (root / "causal_links.jsonl").exists()
    assert (root / "branches.jsonl").exists()
    assert (root / "exposures.jsonl").exists()
    assert (root / "handoffs.jsonl").exists()
    assert (root / "beliefs.jsonl").exists()
    assert (root / "applied_modulations.jsonl").exists()
    assert (root / "regulatory_overrides.jsonl").exists()
    assert (root / "regulatory_state_snapshots.jsonl").exists()
    assert (root / "incidents.jsonl").exists()
    assert (root / "policy_events.jsonl").exists()
    assert (root / "audit_events.jsonl").exists()
    assert (root / "work_items.jsonl").exists()


def test_materializer_checkpoint_written_and_readable(tmp_path):
    """Ch1.5: After run, checkpoint file exists and contains scope keys (incremental mode deferred)."""
    prev = None
    for i in range(2):
        ev = build_envelope("READ", "entity", f"ent_{i}", {}, SCOPE, ACTOR, prev_hash=prev)
        prev = ev["event_id"]
        append_event(ev, tmp_path)
    run_molecules(tmp_path, rebuild=False)
    ck = load_checkpoint(tmp_path, "molecules")
    assert isinstance(ck, dict)
    assert "run/run_mat" in ck or any(k.startswith("run/") for k in ck)
    assert all(isinstance(v, str) for v in ck.values())


def test_materializer_incremental_twice_same_output(tmp_path):
    """Run molecules materializer twice with same ledger (second with rebuild=False); output identical."""
    prev = None
    for i in range(3):
        ev = build_envelope("READ", "entity", f"ent_{i}", {}, SCOPE, ACTOR, prev_hash=prev)
        prev = ev["event_id"]
        append_event(ev, tmp_path)
    run_molecules(tmp_path, rebuild=True)
    root = get_materialized_root(tmp_path)
    out1 = (root / "molecules.jsonl").read_text(encoding="utf-8")
    run_molecules(tmp_path, rebuild=False)
    out2 = (root / "molecules.jsonl").read_text(encoding="utf-8")
    assert out1 == out2


def test_materializer_incremental_matches_full_rebuild(tmp_path):
    """Append one event; run with rebuild=False; output equals full rebuild. See Ch1.5 TESTS/00_test_plan.md."""
    prev = None
    for i in range(2):
        ev = build_envelope("READ", "entity", f"ent_{i}", {}, SCOPE, ACTOR, prev_hash=prev)
        prev = ev["event_id"]
        append_event(ev, tmp_path)
    run_molecules(tmp_path, rebuild=True)
    root = get_materialized_root(tmp_path)
    full_out = (root / "molecules.jsonl").read_text(encoding="utf-8")
    ev_new = build_envelope("READ", "entity", "ent_new", {}, SCOPE, ACTOR, prev_hash=prev)
    append_event(ev_new, tmp_path)
    run_molecules(tmp_path, rebuild=False)
    inc_out = (root / "molecules.jsonl").read_text(encoding="utf-8")
    run_molecules(tmp_path, rebuild=True)
    full_out_after = (root / "molecules.jsonl").read_text(encoding="utf-8")
    assert inc_out == full_out_after
    assert "ent_new" in inc_out or any("ent_new" in line for line in inc_out.split("\n"))


def test_decision_materializer_incremental_matches_full_rebuild(tmp_path):
    """Decision materializer: append one DECISION_COMMITTED; incremental output equals full rebuild."""
    ev1 = build_envelope(
        "DECISION_COMMITTED", "decision", "dec_1",
        {"decision_id": "dec_1", "title": "First"}, SCOPE, ACTOR, prev_hash=None,
    )
    append_event(ev1, tmp_path)
    run_decision(tmp_path, rebuild=True)
    root = get_materialized_root(tmp_path)
    out1 = (root / "decisions.jsonl").read_text(encoding="utf-8")
    ev2 = build_envelope(
        "DECISION_COMMITTED", "decision", "dec_2",
        {"decision_id": "dec_2", "title": "Second"}, SCOPE, ACTOR, prev_hash=ev1["event_id"],
    )
    append_event(ev2, tmp_path)
    run_decision(tmp_path, rebuild=False)
    inc_out = (root / "decisions.jsonl").read_text(encoding="utf-8")
    run_decision(tmp_path, rebuild=True)
    full_out = (root / "decisions.jsonl").read_text(encoding="utf-8")
    assert inc_out == full_out
    assert "dec_2" in inc_out and "Second" in inc_out


def test_reputation_materializer_incremental_matches_full_rebuild(tmp_path):
    """Reputation materializer: append one event; incremental output equals full rebuild."""
    ev1 = build_envelope(
        "ESCROW_LOCKED", "node", "n1",
        {"amount": 5.0, "run_id": "r1"}, SCOPE, ACTOR, prev_hash=None,
    )
    append_event(ev1, tmp_path)
    run_reputation(tmp_path, rebuild=True)
    root = get_materialized_root(tmp_path)
    out1 = (root / "reputation_timeseries.jsonl").read_text(encoding="utf-8")
    ev2 = build_envelope(
        "ESCROW_RELEASED", "node", "n1",
        {"amount": 5.0, "run_id": "r1"}, SCOPE, ACTOR, prev_hash=ev1["event_id"],
    )
    append_event(ev2, tmp_path)
    run_reputation(tmp_path, rebuild=False)
    inc_out = (root / "reputation_timeseries.jsonl").read_text(encoding="utf-8")
    run_reputation(tmp_path, rebuild=True)
    full_out = (root / "reputation_timeseries.jsonl").read_text(encoding="utf-8")
    assert inc_out == full_out
    assert "escrow_released" in inc_out
