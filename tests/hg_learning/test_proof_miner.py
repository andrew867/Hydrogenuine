from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_learning.contracts import EXTRACTION_VERSION, LearningSignalType
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.proof_miner import ProofMiner, extract_signals_from_bundle


def test_mine_swarm_outcome_from_bundle(swarm_proof_bundle: Path):
    signals = extract_signals_from_bundle(swarm_proof_bundle)
    swarm = [s for s in signals if s.signal_type == LearningSignalType.SWARM_OUTCOME]
    assert len(swarm) == 1
    assert swarm[0].payload["swarm_run_id"] == "swarm-test-1"
    assert swarm[0].payload["syndrome_count"] == 1
    assert "child_0" in swarm[0].entity_ids


def test_mining_is_idempotent(swarm_proof_bundle: Path, tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    miner = ProofMiner(store, swarm_proof_bundle.parent)
    miner._ingest_bundle_signals(swarm_proof_bundle)
    count_after_first = store.count()
    miner._ingest_bundle_signals(swarm_proof_bundle)
    assert store.count() == count_after_first
    store.close()


def test_extraction_version_bump_remines(swarm_proof_bundle: Path, tmp_path: Path, monkeypatch):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    miner = ProofMiner(store, swarm_proof_bundle.parent)
    miner._ingest_bundle_signals(swarm_proof_bundle)
    v1_count = store.count()

    import hg_learning.contracts as contracts
    import hg_learning.flywheel.proof_miner as miner_mod

    monkeypatch.setattr(contracts, "EXTRACTION_VERSION", EXTRACTION_VERSION + 1)
    monkeypatch.setattr(miner_mod, "EXTRACTION_VERSION", EXTRACTION_VERSION + 1)

    miner._ingest_bundle_signals(swarm_proof_bundle)
    assert store.count() > v1_count
    store.close()


def test_mining_never_reads_unproofed_data(tmp_path: Path):
    raw = tmp_path / "raw_transcript"
    raw.mkdir()
    (raw / "transcript.txt").write_text("unproofed chat log", encoding="utf-8")
    signals = extract_signals_from_bundle(raw)
    assert signals == []


def test_consent_class_inherited(behavioral_proof_bundle: Path):
    signals = extract_signals_from_bundle(behavioral_proof_bundle)
    behavioral = [s for s in signals if s.signal_type == LearningSignalType.BEHAVIORAL_TEST]
    assert len(behavioral) == 1
    from hg_learning.contracts import RetentionClass

    assert behavioral[0].retention_class == RetentionClass.HUMAN_ADJACENT


def test_correction_events_mined(swarm_proof_bundle: Path):
    signals = extract_signals_from_bundle(swarm_proof_bundle)
    corrections = [s for s in signals if s.signal_type == LearningSignalType.CORRECTION_EVENT]
    assert len(corrections) == 1
    assert corrections[0].payload["target_entity"] == "child_0"


def test_mediation_results_minable(tmp_path: Path):
    bundle = tmp_path / "mediation_bundle"
    bundle.mkdir()
    summary = {
        "label": "mediation_test",
        "started_at": "2026-06-10T02:00:00Z",
        "ended_at": "2026-06-10T02:00:01Z",
        "checks_passed": True,
    }
    (bundle / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (bundle / "checks.json").write_text(json.dumps([{"name": "ok", "pass": True}]), encoding="utf-8")
    (bundle / "ENVIRONMENT.json").write_text(json.dumps({}), encoding="utf-8")
    (bundle / "VERSIONS.txt").write_text("test=1\n", encoding="utf-8")
    artifacts = {
        "mediation_results": [
            {
                "entity_id": "child_med",
                "mediator_id": "capability_elicitation",
                "latent_state_class": "hidden_goal",
                "strength": 0.77,
                "result_digest": "abc123",
                "cost_tokens": 42,
            }
        ]
    }
    (bundle / "artifacts.json").write_text(json.dumps(artifacts), encoding="utf-8")
    signals = extract_signals_from_bundle(bundle)
    interventions = [s for s in signals if s.signal_type == LearningSignalType.INTERVENTION_OUTCOME]
    assert len(interventions) == 1
    assert interventions[0].payload["mediator_id"] == "capability_elicitation"
    assert interventions[0].entity_ids == ["child_med"]


def test_ingest_bundle_creates_signals(swarm_proof_bundle: Path, tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    miner = ProofMiner(store, swarm_proof_bundle.parent)
    created, deduped = miner._ingest_bundle_with_counts(swarm_proof_bundle)
    assert created >= 2
    assert deduped == 0
    created2, deduped2 = miner._ingest_bundle_with_counts(swarm_proof_bundle)
    assert created2 == 0
    assert deduped2 >= 2
    store.close()
