from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from hg_learning.contracts import (
    CorpusOrigin,
    LearningSignalType,
    OutcomeVerdict,
)
from hg_learning.evolution.track_record import MIN_SAMPLES, TrackRecordLedger
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from hg_learning.flywheel.proof_miner import extract_signals_from_bundle


def _ledger(tmp_path: Path, bundle: Path) -> TrackRecordLedger:
    db = tmp_path / "learning.sqlite3"
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    for sig in extract_signals_from_bundle(bundle):
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="proofs/swarm")
        inferred = labeler.infer_automated_label(sig)
        if inferred:
            verdict, conf = inferred
            labeler.label_automated(sig.signal_id, verdict, confidence=conf)
    return TrackRecordLedger(corpus, labeler)


def test_ledger_windows_computed_correctly(swarm_proof_bundle: Path, tmp_path: Path):
    ledger = _ledger(tmp_path, swarm_proof_bundle)
    entities = ledger.list_entity_ids()
    assert entities
    records = ledger.compute(entities[0])
    assert "7d" in records
    assert "30d" in records
    assert "lifetime" in records
    assert records["lifetime"].sample_count >= 1


def test_no_conclusions_below_min_samples(swarm_proof_bundle: Path, tmp_path: Path):
    ledger = _ledger(tmp_path, swarm_proof_bundle)
    entity = ledger.list_entity_ids()[0]
    record = ledger.compute(entity)["lifetime"]
    if record.sample_count < MIN_SAMPLES:
        assert record.sufficient_data is False
        assert record.metrics["syndrome_rate"] == "insufficient_data"


def test_ledger_updates_incrementally(swarm_proof_bundle: Path, tmp_path: Path):
    db = tmp_path / "learning.sqlite3"
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = TrackRecordLedger(corpus, labeler)
    sigs = extract_signals_from_bundle(swarm_proof_bundle)
    corpus.append(sigs[0], origin=CorpusOrigin.MINED, bundle_path="p")
    labeler.sync_corpus_labels()
    entities_before = ledger.list_entity_ids()
    n_before = (
        ledger.compute(entities_before[0])["lifetime"].sample_count
        if entities_before
        else 0
    )
    for sig in sigs[1:]:
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="p")
        labeler.sync_corpus_labels()
    entities = ledger.list_entity_ids()
    if entities:
        n_after = ledger.compute(entities[0])["lifetime"].sample_count
        assert n_after >= n_before


def test_peer_verification_quality_tracked(swarm_proof_bundle: Path, tmp_path: Path):
    ledger = _ledger(tmp_path, swarm_proof_bundle)
    for entity in ledger.list_entity_ids():
        rec = ledger.compute(entity)["lifetime"]
        assert "peer_verification_quality" in rec.metrics
        assert "peer_verification_samples" in rec.metrics
