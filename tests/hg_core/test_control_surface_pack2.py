"""
Control Surface Pack 2: Reference deployments & demo seeds — deterministic seed, replay, bring-up.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.control_surface.demo_seeds import generate_seed, replay_seed_into_ledger


def test_generate_seed_deterministic(tmp_path: Path) -> None:
    """Same seed produces identical seed_events.jsonl (event_ids and content)."""
    out1 = str(tmp_path / "out1")
    out2 = str(tmp_path / "out2")
    generate_seed(out1, seed=1337)
    generate_seed(out2, seed=1337)
    p1 = Path(out1) / "seed_events.jsonl"
    p2 = Path(out2) / "seed_events.jsonl"
    assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")
    events1 = [json.loads(line) for line in p1.read_text(encoding="utf-8").strip().split("\n") if line]
    assert all(e.get("event_id") for e in events1)
    # Different seed -> different content
    generate_seed(str(tmp_path / "out3"), seed=9999)
    p3 = (tmp_path / "out3") / "seed_events.jsonl"
    assert p3.read_text(encoding="utf-8") != p1.read_text(encoding="utf-8")


def test_generate_seed_produces_expected_files(tmp_path: Path) -> None:
    """Seed generator creates seed_events.jsonl, seed_artifacts/, expected_demo_checkpoints.json."""
    summary = generate_seed(str(tmp_path), seed=1337)
    assert (tmp_path / "seed_events.jsonl").exists()
    assert (tmp_path / "seed_artifacts").is_dir()
    assert (tmp_path / "seed_artifacts" / "manifests").is_dir()
    assert (tmp_path / "expected_demo_checkpoints.json").exists()
    assert summary["events_count"] > 0
    assert summary["checkpoints_count"] >= 1
    events = [json.loads(line) for line in (tmp_path / "seed_events.jsonl").read_text(encoding="utf-8").strip().split("\n") if line]
    scopes = {ev.get("scope", {}).get("id") for ev in events}
    assert "swarm_alpha" in scopes
    assert "swarm_beta" in scopes
    assert "demo_run" in scopes
    actions = [ev.get("action") for ev in events]
    assert "WORK_ITEM_CREATED" in actions
    assert "INCIDENT_CANDIDATE_CREATED" in actions
    assert "DISPUTE_OPENED" in actions
    assert "SETTLEMENT_PUBLISHED" in actions
    assert "AUDIT_BUNDLE_EXPORTED" in actions


def test_expected_demo_checkpoints_valid(tmp_path: Path) -> None:
    """expected_demo_checkpoints.json is valid and has required checkpoint fields."""
    generate_seed(str(tmp_path), seed=1337)
    data = json.loads((tmp_path / "expected_demo_checkpoints.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    for cp in data:
        assert "id" in cp
        assert "description" in cp


def test_replay_seed_into_ledger(tmp_path: Path) -> None:
    """Replay appends events to ledger and returns event_ids."""
    generate_seed(str(tmp_path), seed=1337)
    seed_path = tmp_path / "seed_events.jsonl"
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    appended = replay_seed_into_ledger(seed_path, workspace)
    assert len(appended) > 0
    ledger_root = workspace / "memory" / "ledger" / "scopes" / "run"
    assert ledger_root.exists()
    # Should have swarm_alpha, swarm_beta, demo_run
    scope_files = list(ledger_root.glob("*.jsonl"))
    assert len(scope_files) >= 1
    total_lines = 0
    for f in scope_files:
        total_lines += sum(1 for _ in f.read_text(encoding="utf-8").strip().split("\n") if _.strip())
    assert total_lines == len(appended)


def test_bring_up_creates_structure(tmp_path: Path) -> None:
    """Bring-up creates demo_seeds, ledger scopes, materialized, entity_registry."""
    from hg_core.control_surface.demo_seeds.bring_up import main
    exit_code = main(tmp_path, seed=1337)
    assert exit_code == 0
    assert (tmp_path / "memory" / "demo_seeds" / "seed_events.jsonl").exists()
    assert (tmp_path / "memory" / "ledger" / "scopes" / "run").exists()
    assert (tmp_path / "memory" / "materialized" / "work_items.jsonl").exists()
    assert (tmp_path / "memory" / "materialized" / "incidents.jsonl").exists()
    assert (tmp_path / "memory" / "overseer" / "entity_registry.json").exists()
    reg = json.loads((tmp_path / "memory" / "overseer" / "entity_registry.json").read_text(encoding="utf-8"))
    assert len(reg.get("entities", [])) == 8
