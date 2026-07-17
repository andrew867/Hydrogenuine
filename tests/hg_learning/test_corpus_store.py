from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.contracts import (
    CorpusOrigin,
    LearningSignal,
    LearningSignalType,
    RetentionClass,
)
from hg_learning.flywheel.corpus_store import CorpusStore


def _signal(bundle_id: str = "b1", suffix: str = "") -> LearningSignal:
    return LearningSignal(
        signal_id=f"ls_test_{suffix}",
        bundle_id=bundle_id,
        signal_type=LearningSignalType.SWARM_OUTCOME,
        payload={"label": "x", "suffix": suffix},
        retention_class=RetentionClass.STANDARD,
        entity_ids=["e1"],
        observed_at="2026-06-10T00:00:00Z",
    )


def test_corpus_append_only(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    entry, created = store.append(_signal(), origin=CorpusOrigin.MINED, bundle_path="proofs/out/x")
    assert created is True
    loaded = store.get(entry.entry_id)
    assert loaded is not None
    assert loaded.signal.payload["label"] == "x"
    assert store.count() == 1
    store.close()


def test_corpus_dedupe_on_reappend(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    _e1, c1 = store.append(_signal(), origin=CorpusOrigin.MINED, bundle_path="p1")
    _e2, c2 = store.append(_signal(), origin=CorpusOrigin.MINED, bundle_path="p1")
    assert c1 is True
    assert c2 is False
    assert store.count() == 1
    store.close()


def test_synthetic_and_mined_coexist(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    store.append(_signal(suffix="a"), origin=CorpusOrigin.SYNTHETIC, bundle_path="eval/a")
    store.append(_signal(suffix="b", bundle_id="b2"), origin=CorpusOrigin.MINED, bundle_path="proof/b")
    mined = store.query(origin=CorpusOrigin.MINED)
    synthetic = store.query(origin=CorpusOrigin.SYNTHETIC)
    assert len(mined) == 1
    assert len(synthetic) == 1
    store.close()


def test_query_by_entity_and_type(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    store.append(_signal(), origin=CorpusOrigin.MINED, bundle_path="p")
    rows = store.query(signal_type=LearningSignalType.SWARM_OUTCOME, entity_id="e1")
    assert len(rows) == 1
    store.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"n": 1, "s": "hello"},
        {"nested": {"list": [1, 2, 3]}},
        {"unicode": "café"},
    ],
)
def test_corpus_entry_roundtrip(tmp_path: Path, payload: dict):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    sig = LearningSignal(
        signal_id="ls_roundtrip",
        bundle_id="b_rt",
        signal_type=LearningSignalType.CORRECTION_EVENT,
        payload=payload,
        entity_ids=[],
        observed_at="2026-06-10T00:00:00Z",
    )
    entry, _ = store.append(sig, origin=CorpusOrigin.SYNTHETIC, bundle_path="eval/rt")
    loaded = store.get(entry.entry_id)
    assert loaded is not None
    assert loaded.signal.payload == payload
    store.close()
