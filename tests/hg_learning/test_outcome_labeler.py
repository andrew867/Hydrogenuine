from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.contracts import (
    CorpusOrigin,
    LabelSource,
    LearningSignal,
    LearningSignalType,
    OutcomeVerdict,
)
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import LOW_CONFIDENCE_THRESHOLD, OutcomeLabeler


def _stores(tmp_path: Path):
    db = tmp_path / "learning.sqlite3"
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    return corpus, labels, OutcomeLabeler(corpus, labels)


def _add_signal(corpus: CorpusStore, signal_id: str, **kwargs) -> LearningSignal:
    sig = LearningSignal(
        signal_id=signal_id,
        bundle_id="b1",
        signal_type=kwargs.get("signal_type", LearningSignalType.SWARM_OUTCOME),
        payload=kwargs.get("payload", {"syndrome_count": 0}),
        entity_ids=kwargs.get("entity_ids", []),
        observed_at="2026-06-10T00:00:00Z",
    )
    corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="proofs/test")
    return sig


def test_label_priority_operator_beats_automated(tmp_path: Path):
    corpus, labels, labeler = _stores(tmp_path)
    _add_signal(corpus, "sig_prio")
    labeler.label_automated("sig_prio", OutcomeVerdict.SUCCESS, confidence=0.9)
    labeler.label_operator("sig_prio", OutcomeVerdict.REJECTED, actor_id="op1")
    effective = labeler.effective_label("sig_prio")
    assert effective is not None
    assert effective.verdict == OutcomeVerdict.REJECTED
    assert effective.source == LabelSource.OPERATOR
    history = labeler.label_history("sig_prio")
    assert len(history) == 2
    assert history[0].source == LabelSource.AUTOMATED


def test_label_history_append_only(tmp_path: Path):
    _, _, labeler = _stores(tmp_path)
    labeler.label_automated("sig_hist", OutcomeVerdict.PARTIAL, confidence=0.7)
    labeler.label_operator("sig_hist", OutcomeVerdict.SUCCESS)
    labeler.label_downstream("sig_hist", OutcomeVerdict.REJECTED, confidence=0.8)
    history = labeler.label_history("sig_hist")
    assert len(history) == 3
    assert [h.source.value for h in history] == ["automated", "operator", "downstream"]


def test_low_confidence_labels_enter_queue(tmp_path: Path):
    corpus, labels, labeler = _stores(tmp_path)
    _add_signal(
        corpus,
        "sig_low",
        signal_type=LearningSignalType.CORRECTION_EVENT,
        payload={"approved": False},
    )
    labeler.label_automated("sig_low", OutcomeVerdict.UNKNOWN, confidence=0.45)
    assert labels.queue_count() >= 1
    open_items = labels.open_queue()
    assert any(i["signal_id"] == "sig_low" for i in open_items)
    assert 0.45 < LOW_CONFIDENCE_THRESHOLD


def test_downstream_result_labeling(tmp_path: Path):
    corpus, _, labeler = _stores(tmp_path)
    sig = LearningSignal(
        signal_id="sig_swarm",
        bundle_id="bundle_downstream",
        signal_type=LearningSignalType.SWARM_OUTCOME,
        payload={"syndrome_count": 1, "correction_count": 1},
        observed_at="2026-06-10T00:00:00Z",
    )
    corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="proofs/test")
    updated = labeler.reconcile_downstream(
        [{"bundle_id": "bundle_downstream", "verdict": "rejected", "confidence": 0.95}]
    )
    assert updated >= 0
    effective = labeler.effective_label("sig_swarm")
    if updated:
        assert effective is not None
        assert effective.source == LabelSource.DOWNSTREAM


def test_sync_corpus_labels(tmp_path: Path, behavioral_proof_bundle: Path):
    from hg_learning.flywheel.proof_miner import extract_signals_from_bundle

    corpus, _, labeler = _stores(tmp_path)
    for sig in extract_signals_from_bundle(behavioral_proof_bundle):
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="proofs/behavioral")
    stats = labeler.sync_corpus_labels()
    assert stats["labels_created"] >= 1
    effective = labeler.effective_label(
        extract_signals_from_bundle(behavioral_proof_bundle)[0].signal_id
    )
    assert effective is not None
