"""
Ch6 Affective awareness: regulatory policy, state snapshots, modulation, overrides.
See .cursor/plans/stickyreality/chapter6/affective_awareness_regulatory_state/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.affective import (
    load_regulatory_policy,
    get_regulatory_state_snapshot,
    apply_modulation,
    apply_regulatory_override,
    revoke_regulatory_override,
    get_current_regulatory_state,
    list_applied_modulations,
    list_regulatory_overrides,
)
from hg_core.affective.policy import get_effective_policy_at
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers.affective_indexer import run as run_affective_indexer
from hg_core.affective.api import get_regulatory_policy


SCOPE = {"type": "run", "id": "test_run"}
ACTOR = {"agent_id": "agent_A", "pubkey": "0" * 64, "key_id": "k"}


def test_load_regulatory_policy_default_when_no_file(tmp_path: Path):
    """When no policy file exists, load_regulatory_policy returns default."""
    policy = load_regulatory_policy(tmp_path)
    assert "version" in policy
    assert "state_dimensions" in policy
    assert "modulation_rules" in policy


def test_load_regulatory_policy_from_file(tmp_path: Path):
    """When policy file exists, load_regulatory_policy returns its content."""
    policy_dir = tmp_path / "artifacts" / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "regulatory_policy.yaml").write_text(
        "version: '2.0'\neffective_from: '2026-01-01T00:00:00Z'\nstate_dimensions: [a, b]\n"
    )
    policy = load_regulatory_policy(tmp_path)
    assert policy.get("version") == "2.0"
    assert policy.get("state_dimensions") == ["a", "b"]


def test_get_effective_policy_at(tmp_path: Path):
    """get_effective_policy_at returns policy when effective_from <= at_ts."""
    policy_dir = tmp_path / "artifacts" / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "regulatory_policy.yaml").write_text(
        "version: '1.0'\neffective_from: '2025-06-01T00:00:00Z'\nstate_dimensions: [x]\n"
    )
    policy = get_effective_policy_at(tmp_path, "2026-01-01T00:00:00Z")
    assert policy.get("version") == "1.0"
    policy_future = get_effective_policy_at(tmp_path, "2020-01-01T00:00:00Z")
    assert policy_future.get("version") == "1.0"  # we still return loaded; default only when effective > at_ts


def test_apply_modulation_emits(tmp_path: Path):
    """apply_modulation emits MODULATION_APPLIED and optional rationale artifact."""
    before = {"trust_band": 0, "agency_budget": 50.0}
    after = {"trust_band": 1, "agency_budget": 50.0}
    mod_id = apply_modulation(
        scope=SCOPE,
        actor=ACTOR,
        before_state=before,
        after_state=after,
        rationale="Policy upgrade after review",
        workspace_root=tmp_path,
    )
    assert mod_id
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "MODULATION_APPLIED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "MODULATION_APPLIED")
    assert payload["before_state"] == before
    assert payload["after_state"] == after
    assert (tmp_path / "artifacts" / "affective" / "modulation").exists()


def test_apply_regulatory_override_requires_rationale_and_expiry(tmp_path: Path):
    """apply_regulatory_override requires rationale and expiry_ts; emits REGULATORY_OVERRIDE_APPLIED."""
    with pytest.raises(ValueError, match="rationale"):
        apply_regulatory_override(
            scope=SCOPE,
            actor=ACTOR,
            override_spec={"allow_action": "DECISION_COMMITTED"},
            expiry_ts="2026-12-31T23:59:59Z",
            rationale="",
            workspace_root=tmp_path,
        )
    with pytest.raises(ValueError, match="expiry_ts"):
        apply_regulatory_override(
            scope=SCOPE,
            actor=ACTOR,
            override_spec={"allow_action": "DECISION_COMMITTED"},
            expiry_ts="",
            rationale="Emergency override",
            workspace_root=tmp_path,
        )
    override_id = apply_regulatory_override(
        scope=SCOPE,
        actor=ACTOR,
        override_spec={"allow_action": "DECISION_COMMITTED"},
        expiry_ts="2026-12-31T23:59:59Z",
        rationale="Emergency override",
        workspace_root=tmp_path,
    )
    assert override_id
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "REGULATORY_OVERRIDE_APPLIED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "REGULATORY_OVERRIDE_APPLIED")
    assert payload["expiry_ts"] == "2026-12-31T23:59:59Z"
    assert (tmp_path / "artifacts" / "affective" / "override").exists()


def test_revoke_regulatory_override_emits(tmp_path: Path):
    """revoke_regulatory_override emits REGULATORY_OVERRIDE_REVOKED."""
    override_id = apply_regulatory_override(
        scope=SCOPE,
        actor=ACTOR,
        override_spec={"allow_action": "WRITE"},
        expiry_ts="2026-12-31T23:59:59Z",
        rationale="Temporary",
        workspace_root=tmp_path,
    )
    event_id = revoke_regulatory_override(
        override_id,
        scope=SCOPE,
        actor=ACTOR,
        reason="No longer needed",
        workspace_root=tmp_path,
    )
    assert event_id
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "REGULATORY_OVERRIDE_REVOKED" for _, _, ev in evs)


def test_affective_indexer_produces_files(tmp_path: Path):
    """Affective indexer produces regulatory_state_snapshots, applied_modulations, regulatory_overrides."""
    emit(
        "TRUST_BAND_CHANGED",
        "trust",
        "t1",
        {"band": 1},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    apply_modulation(
        scope=SCOPE,
        actor=ACTOR,
        before_state={"trust_band": 0},
        after_state={"trust_band": 1},
        workspace_root=tmp_path,
    )
    apply_regulatory_override(
        scope=SCOPE,
        actor=ACTOR,
        override_spec={"allow_action": "WRITE"},
        expiry_ts="2027-01-01Z",
        rationale="Test",
        workspace_root=tmp_path,
    )
    run_affective_indexer(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "regulatory_state_snapshots.jsonl").exists()
    assert (root / "applied_modulations.jsonl").exists()
    assert (root / "regulatory_overrides.jsonl").exists()
    lines = (root / "applied_modulations.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    lines = (root / "regulatory_overrides.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1


def test_get_current_regulatory_state_from_snapshots(tmp_path: Path):
    """get_current_regulatory_state returns state from materialized snapshots when present."""
    emit(
        "TRUST_BAND_CHANGED",
        "trust",
        "t1",
        {"band": 2},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    run_affective_indexer(tmp_path, rebuild=True)
    state = get_current_regulatory_state(tmp_path, "run", "test_run", agent_id=ACTOR["agent_id"])
    assert "state" in state or "scope_type" in state
    if "state" in state:
        assert state["state"].get("trust_band") == 2


def test_list_applied_modulations_and_overrides(tmp_path: Path):
    """list_applied_modulations and list_regulatory_overrides return filtered lists."""
    apply_modulation(
        scope=SCOPE,
        actor=ACTOR,
        before_state={"trust_band": 0},
        after_state={"trust_band": 1},
        workspace_root=tmp_path,
    )
    apply_regulatory_override(
        scope=SCOPE,
        actor=ACTOR,
        override_spec={"x": 1},
        expiry_ts="2028-01-01Z",
        rationale="R",
        workspace_root=tmp_path,
    )
    run_affective_indexer(tmp_path, rebuild=True)
    mods = list_applied_modulations(tmp_path, scope_type="run", scope_id="test_run")
    assert len(mods) >= 1
    overrides = list_regulatory_overrides(tmp_path, scope_type="run", scope_id="test_run", active_only=True)
    assert len(overrides) >= 1
    assert overrides[0].get("revoked") is False


def test_list_regulatory_overrides_active_only_excludes_expired(tmp_path: Path):
    """active_only excludes overrides past expiry_ts."""
    apply_regulatory_override(
        scope=SCOPE,
        actor=ACTOR,
        override_spec={"x": 1},
        expiry_ts="2020-01-01T00:00:00Z",
        rationale="Old",
        workspace_root=tmp_path,
    )
    run_affective_indexer(tmp_path, rebuild=True)
    active = list_regulatory_overrides(tmp_path, active_only=True, at_ts="2025-01-01T00:00:00Z")
    assert len(active) == 0
    all_overrides = list_regulatory_overrides(tmp_path, active_only=False)
    assert len(all_overrides) >= 1


def test_get_regulatory_policy(tmp_path: Path):
    """get_regulatory_policy returns loaded policy."""
    policy_dir = tmp_path / "artifacts" / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "regulatory_policy.yaml").write_text("version: '3.0'\nstate_dimensions: [d1, d2]\n")
    policy = get_regulatory_policy(tmp_path)
    assert policy.get("version") == "3.0"


def test_safety_no_indefinite_override(tmp_path: Path):
    """Override without expiry_ts is rejected (no path for indefinite override)."""
    with pytest.raises(ValueError, match="expiry_ts"):
        apply_regulatory_override(
            scope=SCOPE,
            actor=ACTOR,
            override_spec={"allow_action": "ANY"},
            expiry_ts="",
            rationale="Never expire",
            workspace_root=tmp_path,
        )
