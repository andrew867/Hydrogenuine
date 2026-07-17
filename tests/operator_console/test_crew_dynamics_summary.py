from pathlib import Path

from hg_gateway import store as store_module
from operator_console.server.app.services.crew_dynamics_summary import build_crew_dynamics_summary


def test_build_crew_dynamics_summary_infers_coordination_and_aggregates_swarm(tmp_path: Path):
    root = tmp_path
    dags = root / "memory" / "automation" / "dags"
    dags.mkdir(parents=True, exist_ok=True)
    (dags / "fourclaw_engage.json").write_text(
        """{
  "graph_id": "fourclaw_engage_v1",
  "version": "1.0",
  "run_policy": {"max_concurrency": 2},
  "checkpoints": ["load_context", "execute_task", "summarize_cycle"]
}
""",
        encoding="utf-8",
    )

    store_module._store = store_module.InMemoryStore()
    store = store_module.get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "turn-1",
            "chat_id": "chat-1",
            "fingerprint_id": "newfoundland_bayman_operational",
            "swarm_run_id": "swarm-1",
            "swarm_role": "orchestrator",
            "relationship_type": "coordination",
            "counterpart_fingerprint_id": "underling_chan_operational",
            "engagement_mode": "reciprocal",
            "created_at": "2026-03-21T12:00:00Z",
        },
    )
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "turn-2",
            "chat_id": "chat-2",
            "fingerprint_id": "newfoundland_bayman_operational",
            "swarm_run_id": "swarm-1",
            "swarm_role": "member",
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "underling_chan_operational",
            "engagement_mode": "reciprocal",
            "created_at": "2026-03-21T12:05:00Z",
        },
    )

    summary = build_crew_dynamics_summary(
        root=root,
        task_name="fourclaw-engage",
        session_target="automation-newfoundland-bayman-fourclaw-engage",
        binding={
            "fingerprint_id": "newfoundland_bayman_operational",
            "operational_agent_id": "newfoundland-bayman",
            "operational_family": "newfoundland-bayman",
        },
    )

    assert summary["status"] == "healthy"
    assert summary["workflow_id"] == "fourclaw_engage"
    assert summary["coordination_style"] == "parallel_contributors"
    assert summary["coordination_style_source"] == "inferred_from_run_policy"
    assert summary["coordination_checkpoints"] == ["load_context", "execute_task", "summarize_cycle"]
    assert summary["swarm_run_id"] == "swarm-1"
    assert summary["swarm_member_count"] == 1
    assert summary["swarm_turn_count"] == 2
    assert summary["swarm_orchestrator_present"] is True
    assert summary["dominant_relationship_type"] == "respect"
    assert summary["dominant_engagement_mode"] == "reciprocal"
