from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.contracts import (
    CorpusOrigin,
    LearningSignal,
    LearningSignalType,
    OutcomeVerdict,
)
from hg_learning.feedback.live_priors import LivePriorsStore
from hg_learning.feedback.prior_resolver import (
    get_effective_value,
    learning_priors_context,
)
from hg_learning.feedback.runner import ShadowFeedbackRunner
from hg_learning.feedback.shadow_ledger import ShadowLedger
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from hg_learning.guardrails.learnable_allowlist import load_allowlist


def _seed_for_live(corpus: CorpusStore, labeler: OutcomeLabeler) -> None:
    for i in range(12):
        sig = LearningSignal(
            signal_id=f"ls_swarm_{i}",
            bundle_id=f"b{i}",
            signal_type=LearningSignalType.SWARM_OUTCOME,
            payload={
                "syndrome_count": 3 if i < 8 else 0,
                "correction_count": 1,
                "verification_graph": {"node_ids": ["a", "b", "c", "d", "e", "f"]},
            },
            entity_ids=["child_0"],
            observed_at="2026-06-10T00:00:00Z",
        )
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="p")
        labeler.label_automated(
            sig.signal_id,
            OutcomeVerdict.SUCCESS if i >= 8 else OutcomeVerdict.PARTIAL,
            confidence=0.8,
        )


@pytest.fixture
def learning_db(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "learning.sqlite3"
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    return db


def test_live_apply_respects_allowlist_bounds(learning_db: Path, monkeypatch):
    monkeypatch.setenv("HG_LEARNING_LIVE_FEEDBACK_ENABLED", "1")
    corpus = CorpusStore(learning_db)
    labels = LabelStore(learning_db)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = ShadowLedger(learning_db)
    live = LivePriorsStore(learning_db)
    _seed_for_live(corpus, labeler)

    report = ShadowFeedbackRunner(corpus, labeler, ledger).run_all()
    assert report.live_applied >= 1
    assert report.bounded_violations == []

    entry = load_allowlist().get("symmetry_breaker.default_delta")
    assert entry is not None
    stored = live.get("symmetry_breaker.default_delta")
    assert stored is not None
    assert entry.floor <= stored <= entry.ceiling


def test_prior_resolver_uses_live_when_enabled(learning_db: Path):
    live = LivePriorsStore(learning_db)
    live.apply(
        parameter="noise_characterizer.tlf_threshold",
        value=0.8,
        path_name="noise_recalibrator",
        adjustment_id="adj1",
    )
    with learning_priors_context(True):
        assert get_effective_value("noise_characterizer.tlf_threshold", 0.75, store=live) == 0.8


def test_prior_resolver_bypassed_for_control_group(learning_db: Path):
    live = LivePriorsStore(learning_db)
    live.apply(
        parameter="noise_characterizer.tlf_threshold",
        value=0.8,
        path_name="noise_recalibrator",
        adjustment_id="adj1",
    )
    with learning_priors_context(False):
        assert get_effective_value("noise_characterizer.tlf_threshold", 0.75, store=live) == 0.75


def test_per_path_live_flag_overrides_master(learning_db: Path, monkeypatch):
    monkeypatch.delenv("HG_LEARNING_LIVE_FEEDBACK_ENABLED", raising=False)
    monkeypatch.setenv("HG_LEARNING_DETECTOR_TUNER_LIVE", "1")
    from hg_learning.feedback.activation import is_path_live

    assert is_path_live("detector_tuner") is True
    assert is_path_live("symmetry_feedback") is False
