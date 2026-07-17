from pathlib import Path

from operator_console.server.app.services.affect_action_summary import build_affect_action_summary
from hg_gateway import store as store_module


def test_build_affect_action_summary_aggregates_affect_and_action_signals(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None

    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "turn-1",
            "chat_id": "chat-1",
            "message_id": "msg-1",
            "fingerprint_id": "newfoundland_bayman_operational",
            "arc_state": "building",
            "engagement_mode": "reciprocal",
            "depth_level": "middle",
            "uncertainty_level": "confident",
            "callback_surface": True,
            "proactive_notice": True,
            "lateral_mode": "aside",
            "position_evolution": False,
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "underling_chan_operational",
            "details": {"moves": ["callback:systems"]},
            "created_at": "2026-03-21T12:00:00Z",
        },
    )

    materialized = tmp_path / "memory" / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    (materialized / "regulatory_state_snapshots.jsonl").write_text(
        '{"scope_type":"agent","scope_id":"newfoundland-bayman","agent_id":"newfoundland-bayman","ts":"2026-03-21T12:01:00Z","trust_band":3,"agency_budget":9.5,"escrow_locked":0.0,"incident_points":0.0,"evidence_refs":[]}\n',
        encoding="utf-8",
    )
    policy_dir = tmp_path / "artifacts" / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "regulatory_policy.yaml").write_text(
        "version: '2.0'\neffective_from: '2026-03-21T00:00:00Z'\nstate_dimensions:\n  - trust_band\n  - agency_budget\n  - escrow_locked\n  - incident_points\nmodulation_rules: []\n",
        encoding="utf-8",
    )

    summary = build_affect_action_summary(
        root=tmp_path,
        task_name="newfoundland-bayman-fourclaw-engage",
        session_target="automation-newfoundland-bayman-fourclaw-engage",
        binding={
            "fingerprint_id": "newfoundland_bayman_operational",
            "operational_agent_id": "newfoundland-bayman",
        },
    )

    assert summary["status"] == "healthy"
    assert summary["affective_state"]["trust_band"] == 3
    assert summary["affective_state"]["agency_budget"] == 9.5
    assert summary["action_state"]["dominant_arc_state"] == "building"
    assert summary["action_state"]["dominant_engagement_mode"] == "reciprocal"
    assert summary["latest_turn"]["relationship_type"] == "respect"
