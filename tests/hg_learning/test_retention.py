from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from hg_learning.contracts import (
    CorpusOrigin,
    LearningSignal,
    LearningSignalType,
    RetentionClass,
)
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.retention import RetentionPolicy, scrub_pii


def _entry(
    store: CorpusStore,
    *,
    signal_id: str,
    retention: RetentionClass,
    ingested_at: str,
) -> None:
    sig = LearningSignal(
        signal_id=signal_id,
        bundle_id="b1",
        signal_type=LearningSignalType.SWARM_OUTCOME,
        payload={"k": signal_id},
        retention_class=retention,
        observed_at=ingested_at,
    )
    store.append(sig, origin=CorpusOrigin.MINED, bundle_path="p")


def test_scrub_pii():
    dirty = {
        "email": "user@example.com",
        "phone": "555-123-4567",
        "nested": ["call +1 (555) 987-6543"],
    }
    clean = scrub_pii(dirty)
    assert "example.com" not in str(clean)
    assert "[REDACTED_EMAIL]" in clean["email"]
    assert "[REDACTED_PHONE]" in clean["phone"]


def test_retention_purge_expired(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat().replace("+00:00", "Z")
    recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _entry(store, signal_id="old_sig", retention=RetentionClass.STANDARD, ingested_at=old)
    _entry(store, signal_id="new_sig", retention=RetentionClass.STANDARD, ingested_at=recent)
    assert store.count() == 2

    policy = RetentionPolicy()
    report = policy.purge_expired(store)
    assert report.purged == 1
    assert store.count() == 1
    assert store.get_signal("new_sig") is not None
    store.close()


def test_retention_purge_spares_referenced_signals(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat().replace("+00:00", "Z")
    _entry(store, signal_id="cited_sig", retention=RetentionClass.STANDARD, ingested_at=old)
    policy = RetentionPolicy()
    report = policy.purge_expired(store, referenced_signal_ids={"cited_sig"})
    assert report.purged == 0
    assert report.retained_holds == 1
    assert "cited_sig" in report.holds
    assert store.count() == 1
    store.close()


def test_proof_locked_never_purged(tmp_path: Path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat().replace("+00:00", "Z")
    _entry(store, signal_id="locked", retention=RetentionClass.PROOF_LOCKED, ingested_at=old)
    policy = RetentionPolicy()
    report = policy.purge_expired(store)
    assert report.purged == 0
    assert report.retained_proof_locked == 1
    assert store.count() == 1
    store.close()
