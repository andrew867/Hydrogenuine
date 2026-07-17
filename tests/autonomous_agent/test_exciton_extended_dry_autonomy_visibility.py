"""EXCITON extended dry autonomy visibility tests."""

from __future__ import annotations

import json

from hg_runtime.exciton.agent_zero_extended_dry_autonomy_data_sources import build_agent_zero_extended_dry_autonomy_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState


def test_missing_run_is_red():
    panels = build_agent_zero_extended_dry_autonomy_panels(CollectorContext(offline_fixture=True))
    assert len(panels) == 1
    p = panels[0]
    assert p.panel_id == "AgentZeroExtendedDryAutonomyMonitorPanel"
    assert p.state == ExcitonPanelState.RED
    assert p.fields.get("publish_available") is False
    assert p.fields.get("send_available") is False


def test_snapshot_panel_no_publish_buttons(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    run_id = "exciton-run"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_RUN_ID", run_id)
    root = ext / run_id
    root.mkdir(parents=True)
    snap = {
        "panel_id": "AgentZeroExtendedDryAutonomyMonitorPanel",
        "verdict": "YELLOW_EXTENDED_DRY_AUTONOMY_PROVIDER_UNAVAILABLE",
        "publish_available": False,
        "send_available": False,
    }
    (root / "exciton_snapshot.json").write_text(json.dumps(snap), encoding="utf-8")
    (root / "heartbeats.jsonl").write_text(
        json.dumps({"observed_at": "2026-06-18T12:00:00+00:00", "verdict": snap["verdict"]}) + "\n",
        encoding="utf-8",
    )
    (root / "anchor_audit.json").write_text(json.dumps({"verdict": "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"}), encoding="utf-8")
    panels = build_agent_zero_extended_dry_autonomy_panels(CollectorContext(offline_fixture=False))
    fields = panels[0].fields
    assert fields.get("publish_available") is False
    assert fields.get("direct_external_actions_allowed") is False
    assert fields.get("remote_anchor_status", "").startswith("YELLOW_")
