from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hg_learning.contracts import CorpusOrigin, LearningSignal, LearningSignalType, OutcomeVerdict
from hg_learning.evolution.fingerprint_evolver import FingerprintEvolver
from hg_learning.evolution.lineage import LineageStore
from hg_learning.evolution.track_record import TrackRecordLedger
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from hg_cognition.drift_handshake import reset_expected_change_registry, default_expected_change_registry
from hg_cognition.detectors.base import DetectorContext
from hg_cognition.detectors.drift import IntentDriftDetector
from hg_cognition.embeddings.hashing import hash_embed


@pytest.fixture
def learning_db(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "learning.sqlite3"
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    return db


def _profile() -> dict:
    return {
        "cognitive_fingerprint": {
            "agreement_tendency": 0.5,
            "analysis_vs_intuition": 0.5,
            "quantum_cognitive_profile": {"noise_resilience": 0.5, "symmetry_breaking_role": "neutral"},
            "embodiment_profile": {"physical_caution": 0.7},
        },
    }


def _seed_entity_corpus(corpus: CorpusStore, labeler: OutcomeLabeler, entity_id: str, *, count: int = 25) -> None:
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for i in range(count):
        ts = (base + timedelta(days=i % 10)).isoformat().replace("+00:00", "Z")
        sig = LearningSignal(
            signal_id=f"sig_{entity_id}_{i}",
            bundle_id=f"b{i}",
            signal_type=LearningSignalType.SWARM_OUTCOME if i % 2 == 0 else LearningSignalType.BEHAVIORAL_TEST,
            payload={"syndrome_count": 3 if i < 15 else 0, "task_completion": 1.0},
            entity_ids=[entity_id],
            observed_at=ts,
        )
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="p")
        verdict = OutcomeVerdict.SUCCESS if i >= 12 else OutcomeVerdict.PARTIAL
        labeler.label_automated(sig.signal_id, verdict, confidence=0.85)


def _evolver(db: Path) -> FingerprintEvolver:
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    return FingerprintEvolver(corpus, labeler, TrackRecordLedger(corpus, labeler), LineageStore(db))


def test_propose_returns_none_without_evidence(learning_db: Path):
    evolver = _evolver(learning_db)
    proposal, reason = evolver.propose("entity_x", _profile())
    assert proposal is None
    assert reason == "insufficient_track_record"


def test_proposal_cites_evidence_and_respects_caps(learning_db: Path):
    corpus = CorpusStore(learning_db)
    labels = LabelStore(learning_db)
    labeler = OutcomeLabeler(corpus, labels)
    _seed_entity_corpus(corpus, labeler, "entity_y")
    evolver = _evolver(learning_db)
    proposal, reason = evolver.propose("entity_y", _profile())
    assert reason is None
    assert proposal is not None
    assert len(proposal.evidence_signal_ids) >= 20
    for path, delta in proposal.trait_deltas.items():
        assert abs(delta) <= 0.10


def test_end_to_end_approve_and_rollback(learning_db: Path):
    reset_expected_change_registry()
    corpus = CorpusStore(learning_db)
    labels = LabelStore(learning_db)
    labeler = OutcomeLabeler(corpus, labels)
    _seed_entity_corpus(corpus, labeler, "entity_z")
    evolver = _evolver(learning_db)
    proposal, _ = evolver.propose("entity_z", _profile())
    assert proposal is not None
    result = evolver.approve_proposal(proposal.proposal_id, operator_id="operator")
    assert result["ok"] is True
    child_id = result["child_fingerprint_id"]
    registry = default_expected_change_registry()
    assert registry.is_suppressed("entity_z", child_id)
    rollback = evolver.rollback("entity_z", operator_id="operator")
    assert rollback["ok"] is True


def test_drift_handshake_suppresses_detector(learning_db: Path):
    reset_expected_change_registry()
    registry = default_expected_change_registry()
    registry.register(entity_id="e1", old_fingerprint_id="fp_old", new_fingerprint_id="fp_new")
    ctx = DetectorContext(
        correlation_id="c1",
        baseline_intent_vec=hash_embed("baseline"),
        baseline_response_vec=hash_embed("response"),
        baseline_diversity=0.5,
        baseline_alternatives=0.5,
        denied_intent_centroids=[],
        entity_id="e1",
        fingerprint_id="fp_new",
        evolution_change_suppressed=registry.is_suppressed("e1", "fp_new"),
    )
    score = IntentDriftDetector().run([], ctx)
    assert score.level == 0
