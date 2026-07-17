"""
Ch2 Observation pipeline: registry, ingest, anomaly, indexer, API, tamper, access.
See .cursor/plans/stickyreality/chapter2/sensory_awareness_observation_pipeline/
"""

from __future__ import annotations

import json
import hashlib
import pytest
from pathlib import Path

from hg_core.observations import (
    SignalDefinition,
    SignalRegistry,
    load_registry,
    write_observation_artifact,
    write_rationale_artifact,
    ingest_observation,
    detect_anomalies,
    integrity_rule,
    expected_range_rule,
    emit_observation_bound,
    list_observations,
    get_observation,
)
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers.observations_indexer import run as run_observations_indexer


def _make_registry(tmp_path: Path, signals: list) -> SignalRegistry:
    import yaml
    reg_path = tmp_path / "signals.yaml"
    data = {"signals": []}
    for s in signals:
        data["signals"].append({
            "signal_id": s["signal_id"],
            "name": s.get("name", s["signal_id"]),
            "type": s["type"],
            "schema": s.get("schema", {}),
            "reliability": s.get("reliability", 0.8),
            "pii_class": s.get("pii_class", "none"),
            "retention_policy_id": s.get("retention_policy_id", "default"),
        })
    reg_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    return load_registry(reg_path)


def test_registry_load(tmp_path: Path):
    """Registry load from YAML; get/list_ids work."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "Sig1", "type": "metric", "schema": {}, "reliability": 0.9, "pii_class": "none", "retention_policy_id": "default"},
    ])
    assert "s1" in reg
    assert reg.list_ids() == ["s1"]
    sd = reg.get("s1")
    assert sd.signal_id == "s1"
    assert sd.reliability == 0.9
    with pytest.raises(KeyError):
        reg.get("unknown")


def test_registry_empty_path(tmp_path: Path):
    """Load from non-existent path returns empty registry."""
    reg = load_registry(tmp_path / "nonexistent.yaml")
    assert reg.list_ids() == []
    with pytest.raises(KeyError):
        reg.get("any")


def test_artifact_write_observation(tmp_path: Path):
    """write_observation_artifact returns path, checksum, size."""
    out = write_observation_artifact(tmp_path, "obs_abc", b"hello", ext="bin")
    assert "path" in out
    assert "checksum" in out
    assert out["checksum"].startswith("sha256:")
    assert out["size_bytes"] == 5
    assert (tmp_path / "artifacts" / "observations" / "raw").exists()


def test_artifact_write_rationale(tmp_path: Path):
    """write_rationale_artifact writes JSON and returns artifact_id."""
    out = write_rationale_artifact(tmp_path, "anom_1", {"rule_id": "r1", "metrics": {}})
    assert out["artifact_id"] == "anom_1"
    assert "path" in out


def test_ingest_emits_observation_recorded(tmp_path: Path):
    """ingest_observation emits OBSERVATION_RECORDED with scope and payload_ref."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "sig1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "run1"}
    actor = {"agent_id": "test", "pubkey": "0" * 64, "key_id": "k"}
    obs_id = ingest_observation(
        tmp_path, "sig1", scope, actor, reg,
        payload_bytes=b"payload",
        source={"type": "inline"},
    )
    assert obs_id
    evs = list(iter_events_by_scope(tmp_path))
    assert len(evs) >= 1
    actions = [ev.get("action") for _, _, ev in evs]
    assert "OBSERVATION_RECORDED" in actions
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "OBSERVATION_RECORDED")
    assert payload["observation_id"] == obs_id
    assert payload["signal_id"] == "sig1"
    assert "payload_ref" in payload and "path" in payload["payload_ref"]


def test_anomaly_rule_emits_anomaly_detected(tmp_path: Path):
    """detect_anomalies with integrity_rule on mismatched artifact emits ANOMALY_DETECTED."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "r1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    obs_id = ingest_observation(tmp_path, "s1", scope, actor, reg, payload_bytes=b"original", source={"type": "inline"})
    evs = list(iter_events_by_scope(tmp_path))
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "OBSERVATION_RECORDED")
    art_path = payload["payload_ref"]["path"]
    Path(art_path).write_bytes(b"tampered")
    observation_row = {**payload, "integrity": {"payload_sha256": hashlib.sha256(b"original").hexdigest()}}
    rules = [
        ("integrity", "high", "Artifact hash mismatch", integrity_rule),
    ]
    ids = detect_anomalies(observation_row, rules, scope=scope, actor=actor, workspace_root=tmp_path)
    assert len(ids) == 1
    evs2 = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "ANOMALY_DETECTED" for _, _, ev in evs2)


def test_ingest_to_indexer_to_api(tmp_path: Path):
    """ingest -> ledger -> indexer -> list_observations returns same observation."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "run1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    obs_id = ingest_observation(tmp_path, "s1", scope, actor, reg, payload_bytes=b"data", source={"type": "inline"})
    run_observations_indexer(tmp_path, rebuild=True)
    listed = list_observations(tmp_path)
    assert len(listed) == 1
    assert listed[0]["observation_id"] == obs_id
    assert get_observation(tmp_path, obs_id) is not None
    assert get_observation(tmp_path, "nonexistent") is None


def test_tamper_integrity_mismatch_triggers_anomaly(tmp_path: Path):
    """Modify artifact after ingest; integrity_rule detects mismatch."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "r1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    ingest_observation(tmp_path, "s1", scope, actor, reg, payload_bytes=b"correct", source={"type": "inline"})
    evs = list(iter_events_by_scope(tmp_path))
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "OBSERVATION_RECORDED")
    path = Path(payload["payload_ref"]["path"])
    path.write_bytes(b"tampered_content")
    obs_row = {**payload, "integrity": {"payload_sha256": hashlib.sha256(b"correct").hexdigest()}}
    rules = [("integrity", "high", "Integrity check", integrity_rule)]
    detect_anomalies(obs_row, rules, scope=scope, actor=actor, workspace_root=tmp_path)
    evs2 = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "ANOMALY_DETECTED" for _, _, ev in evs2)


def test_high_pii_hidden_by_default(tmp_path: Path):
    """List/get with high pii_class redacts payload_ref unless reveal=True."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "high", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "r1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    ingest_observation(tmp_path, "s1", scope, actor, reg, payload_bytes=b"secret", source={"type": "inline"})
    run_observations_indexer(tmp_path, rebuild=True)
    listed = list_observations(tmp_path)
    assert len(listed) == 1
    assert listed[0].get("payload_ref", {}).get("redacted") is True
    detail = get_observation(tmp_path, listed[0]["observation_id"], reveal=False)
    assert detail and detail.get("payload_ref", {}).get("redacted") is True


def test_reveal_emits_audited_event(tmp_path: Path):
    """get_observation(..., reveal=True) returns full row and emits SENSITIVE_REVEAL_REQUESTED."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "high", "retention_policy_id": "default"},
    ])
    scope = {"type": "run", "id": "r1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    obs_id = ingest_observation(tmp_path, "s1", scope, actor, reg, payload_bytes=b"secret", source={"type": "inline"})
    run_observations_indexer(tmp_path, rebuild=True)
    detail = get_observation(tmp_path, obs_id, reveal=True, scope=scope, actor=actor)
    assert detail is not None
    assert detail.get("payload_ref", {}).get("redacted") is not True
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "SENSITIVE_REVEAL_REQUESTED" for _, _, ev in evs)


def test_emit_observation_bound(tmp_path: Path):
    """emit_observation_bound emits OBSERVATION_BOUND; indexer includes it."""
    from hg_core.ledger import emit
    scope = {"type": "run", "id": "r1"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    emit(
        "OBSERVATION_RECORDED",
        "observation", "obs_x",
        {"observation_id": "obs_x", "signal_id": "s1", "ts_observed": "2026-01-01T00:00:00Z", "ts_ingested": "2026-01-01T00:00:00Z", "source": {}, "integrity": {}, "quality": {"reliability": 0.8, "completeness": 1.0, "parse_errors": []}, "labels": []},
        scope=scope, actor=actor, workspace_root=tmp_path,
    )
    emit_observation_bound("obs_x", entity_id="ent_1", scope=scope, actor=actor, workspace_root=tmp_path)
    run_observations_indexer(tmp_path, rebuild=True)
    bindings_path = tmp_path / "memory" / "materialized" / "bindings.jsonl"
    assert bindings_path.exists()
    lines = [json.loads(l) for l in bindings_path.read_text().strip().split("\n") if l]
    assert any(b.get("observation_id") == "obs_x" and b.get("entity_id") == "ent_1" for b in lines)


def test_list_observations_filter(tmp_path: Path):
    """list_observations with scope_type/scope_id/signal_id filter."""
    reg = _make_registry(tmp_path, [
        {"signal_id": "s1", "name": "S1", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
        {"signal_id": "s2", "name": "S2", "type": "metric", "schema": {}, "reliability": 0.8, "pii_class": "none", "retention_policy_id": "default"},
    ])
    scope1 = {"type": "run", "id": "run1"}
    scope2 = {"type": "run", "id": "run2"}
    actor = {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"}
    ingest_observation(tmp_path, "s1", scope1, actor, reg, payload_bytes=b"1", source={"type": "inline"})
    ingest_observation(tmp_path, "s2", scope1, actor, reg, payload_bytes=b"2", source={"type": "inline"})
    ingest_observation(tmp_path, "s1", scope2, actor, reg, payload_bytes=b"3", source={"type": "inline"})
    run_observations_indexer(tmp_path, rebuild=True)
    assert len(list_observations(tmp_path)) == 3
    assert len(list_observations(tmp_path, scope_id="run1")) == 2
    assert len(list_observations(tmp_path, signal_id="s1")) == 2
    assert len(list_observations(tmp_path, scope_id="run2", signal_id="s1")) == 1
