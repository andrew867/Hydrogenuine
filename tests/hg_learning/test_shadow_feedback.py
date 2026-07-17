from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.contracts import (
    CorpusOrigin,
    LearningSignal,
    LearningSignalType,
    OutcomeVerdict,
)
from hg_learning.feedback.runner import ShadowFeedbackRunner
from hg_learning.feedback.shadow_ledger import ShadowLedger
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from hg_quantum.noise_model import tlf_detector


def _seed_corpus(corpus: CorpusStore, labeler: OutcomeLabeler) -> None:
    swarm = LearningSignal(
        signal_id="ls_swarm1",
        bundle_id="b1",
        signal_type=LearningSignalType.SWARM_OUTCOME,
        payload={
            "syndrome_count": 2,
            "correction_count": 1,
            "verification_graph": {"node_ids": ["a", "b", "c", "d", "e", "f"]},
        },
        entity_ids=["child_0"],
        observed_at="2026-06-10T00:00:00Z",
    )
    corpus.append(swarm, origin=CorpusOrigin.MINED, bundle_path="p")
    labeler.label_automated("ls_swarm1", OutcomeVerdict.PARTIAL, confidence=0.7)
    noise = LearningSignal(
        signal_id="ls_noise1",
        bundle_id="b2",
        signal_type=LearningSignalType.NOISE_EPISODE,
        payload={"assigned": "entity_c"},
        entity_ids=["entity_c"],
        observed_at="2026-06-10T00:00:00Z",
    )
    corpus.append(noise, origin=CorpusOrigin.MINED, bundle_path="p")
    labeler.label_automated("ls_noise1", OutcomeVerdict.SUCCESS, confidence=0.8)
    intervention = LearningSignal(
        signal_id="ls_int1",
        bundle_id="b3",
        signal_type=LearningSignalType.INTERVENTION_OUTCOME,
        payload={"interventions": [{"status": "pending_approval"}]},
        observed_at="2026-06-10T00:00:00Z",
    )
    corpus.append(intervention, origin=CorpusOrigin.MINED, bundle_path="p")
    labeler.label_operator("ls_int1", OutcomeVerdict.REJECTED, actor_id="op")


def test_shadow_mode_writes_ledger_only(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(tlf_detector, "TLF_THRESHOLD", 0.75)
    db = tmp_path / "learning.sqlite3"
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = ShadowLedger(db)
    _seed_corpus(corpus, labeler)
    before = tlf_detector.TLF_THRESHOLD
    runner = ShadowFeedbackRunner(corpus, labeler, ledger)
    report = runner.run_all()
    assert report.paths_run == 5
    assert ledger.count() >= 1
    assert tlf_detector.TLF_THRESHOLD == before


@pytest.mark.parametrize(
    "path_name",
    [
        "symmetry_feedback",
        "sizing_feedback",
        "graph_feedback",
        "noise_recalibrator",
        "detector_tuner",
    ],
)
def test_each_path_runs(tmp_path: Path, path_name: str):
    db = tmp_path / f"{path_name}.sqlite3"
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = ShadowLedger(db)
    _seed_corpus(corpus, labeler)
    report = ShadowFeedbackRunner(corpus, labeler, ledger).run_all()
    names = [r.path_name for r in report.results]
    assert path_name in names
