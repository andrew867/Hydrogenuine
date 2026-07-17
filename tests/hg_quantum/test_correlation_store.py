from __future__ import annotations

from pathlib import Path

from hg_quantum.entanglement.contracts import CorrelationStrength, EntangledPair
from hg_quantum.persistence.correlation_store import CorrelationStore


def test_correlation_store_roundtrip(tmp_path: Path):
    store = CorrelationStore(tmp_path / "corr.sqlite3")
    pair = EntangledPair("p1", "a", "b", "fp1", "swarm_siblings", 0.95)
    store.save_pair(pair)
    loaded = store.get_pair("a", "b")
    assert loaded is not None
    assert loaded.pair_id == "p1"
    strength = CorrelationStrength("a", "b", 0.88, {"emotional": 0.9}, "2026-06-09T00:00:00Z")
    store.save_measurement(strength)
    latest = store.latest_measurement("a", "b")
    assert latest is not None
    assert latest.coefficient == 0.88
    store.close()
