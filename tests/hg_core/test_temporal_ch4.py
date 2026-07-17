"""
Ch4 Temporal awareness: episodes, belief snapshots, causal links, branches, timeline, audit export.
See .cursor/plans/stickyreality/chapter4/temporal_awareness_time_memory/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.temporal import (
    start_episode,
    end_episode,
    build_belief_snapshot,
    record_causal_link,
    propose_branch,
    record_branch_prediction,
    close_branch,
    list_episodes,
    get_episode,
    get_timeline,
    get_belief_snapshot_at,
    list_causal_links,
    list_branches,
    export_temporal_audit,
)
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers.temporal_indexer import run as run_temporal_indexer


SCOPE = {"type": "run", "id": "test_run"}
ACTOR = {"agent_id": "test", "pubkey": "0" * 64, "key_id": "k"}


def test_episode_start_end(tmp_path: Path):
    """start_episode and end_episode emit EPISODE_STARTED, EPISODE_ENDED; optional summary -> EPISODE_SUMMARY_PUBLISHED."""
    ep_id = start_episode(name="Run 1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ep_id
    end_episode(episode_id=ep_id, scope=SCOPE, actor=ACTOR, summary={"key_decisions": ["d1"]}, workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    actions = [ev.get("action") for _, _, ev in evs]
    assert "EPISODE_STARTED" in actions
    assert "EPISODE_ENDED" in actions
    assert "EPISODE_SUMMARY_PUBLISHED" in actions
    assert (tmp_path / "artifacts" / "temporal" / "episodes").exists()


def test_belief_snapshot_determinism(tmp_path: Path):
    """Belief snapshot at T contains only events with ts <= T; deterministic for same prefix."""
    emit(
        "DECISION_COMMITTED",
        "decision", "dec_1",
        {"decision_id": "dec_1", "title": "D", "based_on_claim_ids": [], "value_weights": [], "context_ref": {}, "produced_artifact_ids": []},
        scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    run_scope = ("run", "test_run")
    evs = [ev for st, sid, ev in iter_events_by_scope(tmp_path) if (st, sid) == run_scope]
    ts_after = evs[0].get("ts", "") + "Z" if evs else "2026-01-01T00:00:00Z"
    snap = build_belief_snapshot(tmp_path, "run", "test_run", ts_after)
    assert snap["at_ts"] == ts_after
    assert len(snap["decisions"]) >= 1
    assert snap["decisions"][0].get("decision_id") == "dec_1"
    snap2 = build_belief_snapshot(tmp_path, "run", "test_run", ts_after)
    assert snap["decisions"] == snap2["decisions"]


def test_causal_link_emission(tmp_path: Path):
    """record_causal_link emits CAUSAL_LINK_RECORDED with mechanism artifact."""
    link_id = record_causal_link(
        cause_refs=[{"type": "decision", "id": "d1"}],
        effect_refs=[{"type": "evaluation", "id": "e1"}],
        strength=0.8,
        link_type="direct",
        status="hypothesized",
        mechanism_notes="Decision d1 led to outcome e1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert link_id
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "CAUSAL_LINK_RECORDED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "CAUSAL_LINK_RECORDED")
    assert payload["link_id"] == link_id
    assert payload["type"] == "direct"
    assert payload["status"] == "hypothesized"


def test_branch_propose_close(tmp_path: Path):
    """propose_branch and close_branch emit BRANCH_PROPOSED, BRANCH_CLOSED."""
    b_id = propose_branch(decision_id="dec_1", option_id="opt_b", scope=SCOPE, actor=ACTOR, notes="Alternative", workspace_root=tmp_path)
    assert b_id
    close_branch(branch_id=b_id, decision_id="dec_1", reason="not_taken", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "BRANCH_PROPOSED" for _, _, ev in evs)
    assert any(ev.get("action") == "BRANCH_CLOSED" for _, _, ev in evs)


def test_branch_prediction_made(tmp_path: Path):
    """record_branch_prediction emits BRANCH_PREDICTION_MADE."""
    b_id = propose_branch(decision_id="dec_1", option_id="opt_b", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    record_branch_prediction(
        branch_id=b_id,
        decision_id="dec_1",
        option_id="opt_b",
        prediction_id="pred_b1",
        metric={"name": "success"},
        expected={"value": 1},
        deadline="2026-12-31",
        confidence=0.7,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "BRANCH_PREDICTION_MADE" for _, _, ev in evs)


def test_timeline_api(tmp_path: Path):
    """Run lifecycle produces timeline; get_timeline returns ordered events."""
    start_episode(name="R1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_temporal_indexer(tmp_path, rebuild=True)
    timeline = get_timeline(tmp_path, scope_type="run", scope_id="test_run")
    assert len(timeline) >= 1
    assert any(t.get("action") == "EPISODE_STARTED" for t in timeline)


def test_snapshot_api_stable_after_rebuild(tmp_path: Path):
    """get_belief_snapshot_at returns stable results; materializer rebuild doesn't change snapshot (ledger prefix)."""
    emit(
        "DECISION_COMMITTED",
        "decision", "dec_s",
        {"decision_id": "dec_s", "title": "S", "based_on_claim_ids": [], "value_weights": [], "context_ref": {}, "produced_artifact_ids": []},
        scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    evs = [ev for st, sid, ev in iter_events_by_scope(tmp_path) if (st, sid) == ("run", "test_run")]
    at_ts = evs[0].get("ts", "9999-12-31T23:59:59Z") if evs else "9999-12-31T23:59:59Z"
    snap1 = get_belief_snapshot_at(tmp_path, "run", "test_run", at_ts)
    run_temporal_indexer(tmp_path, rebuild=True)
    snap2 = get_belief_snapshot_at(tmp_path, "run", "test_run", at_ts)
    assert snap1["decisions"] == snap2["decisions"]


def test_audit_export_includes_event_ids(tmp_path: Path):
    """export_temporal_audit produces artifact and emits TEMPORAL_AUDIT_EXPORTED; bundle has event_ids."""
    start_episode(name="AuditRun", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_temporal_indexer(tmp_path, rebuild=True)
    out = export_temporal_audit(tmp_path, scope_type="run", scope_id="test_run", scope=SCOPE, actor=ACTOR)
    assert "artifact_path" in out
    assert "event_id" in out
    assert Path(out["artifact_path"]).exists()
    bundle = json.loads(Path(out["artifact_path"]).read_text(encoding="utf-8"))
    assert "event_ids" in bundle
    assert "event_count" in bundle
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "TEMPORAL_AUDIT_EXPORTED" for _, _, ev in evs)


def test_list_episodes_and_get_episode(tmp_path: Path):
    """list_episodes and get_episode read from materialized index."""
    ep_id = start_episode(name="E1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    end_episode(episode_id=ep_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_temporal_indexer(tmp_path, rebuild=True)
    eps = list_episodes(tmp_path, scope_id="test_run")
    assert len(eps) >= 1
    ep = get_episode(tmp_path, ep_id)
    assert ep is not None
    assert ep["episode_id"] == ep_id


def test_list_causal_links_and_branches(tmp_path: Path):
    """list_causal_links and list_branches filter by scope/status/decision_id."""
    record_causal_link(
        cause_refs=[], effect_refs=[], strength=0.5, link_type="contributing", status="confirmed",
        mechanism_notes="n", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    propose_branch(decision_id="dx", option_id="oy", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    run_temporal_indexer(tmp_path, rebuild=True)
    links = list_causal_links(tmp_path, scope_id="test_run", status="confirmed")
    assert len(links) >= 1
    branches = list_branches(tmp_path, decision_id="dx")
    assert len(branches) >= 1
