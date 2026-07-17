"""GAPS G1: correlation pairs survive store round-trip and restart."""
from __future__ import annotations

from pathlib import Path

from hg_quantum.entanglement.state_correlator import StateCorrelator
from hg_quantum.persistence.correlation_store import CorrelationStore


def test_entangled_pairs_survive_restart(tmp_path: Path) -> None:
    db = tmp_path / "correlations.sqlite3"
    store1 = CorrelationStore(db)
    correlator1 = StateCorrelator(fingerprint_id="fp-restart", store=store1)
    pair = correlator1.register_pair("entity-a", "entity-b", "swarm_siblings")
    correlator1.measure_correlation("entity-a", "entity-b")
    store1.close()

    store2 = CorrelationStore(db)
    correlator2 = StateCorrelator(fingerprint_id="fp-restart", store=store2)
    restored = correlator2.hydrate_from_store()
    assert restored == 1
    strength = correlator2.measure_correlation("entity-a", "entity-b")
    assert strength.coefficient > 0
    assert pair.pair_id in correlator2._pairs
    store2.close()
