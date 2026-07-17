from __future__ import annotations

from pathlib import Path

from hg_quantum.error_correction.contracts import CorrectionAction, SyndromeReport
from hg_quantum.error_correction.provenance import ProvenanceStore


def test_provenance_append_and_replay(tmp_path: Path):
    store = ProvenanceStore(tmp_path / "prov.jsonl")
    syn = SyndromeReport("s1", "run1", ["a", "b"], 0.9)
    act = CorrectionAction("c1", "s1", "a", 0.5)
    rec = store.append(swarm_run_id="run1", syndromes=[syn], actions=[act], input_fingerprints=["fp1"])
    replayed = store.replay(rec.record_id)
    assert replayed is not None
    assert replayed.swarm_run_id == "run1"
