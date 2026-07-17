"""Property-style tests for deterministic correction decoding (P2-7)."""
from __future__ import annotations

import random

from hg_quantum.error_correction.contracts import SyndromeReport
from hg_quantum.error_correction.correction_decoder import decode_corrections


def test_decode_idempotent_under_permutation():
    rng = random.Random(42)
    for _ in range(40):
        locations = [f"child_{rng.randint(0, 5)}" for _ in range(rng.randint(1, 4))]
        confidence = round(rng.uniform(0.5, 1.0), 3)
        syndromes = [
            SyndromeReport(
                report_id=f"syn_{i}",
                swarm_run_id="prop",
                syndrome_locations=locations,
                confidence=confidence,
            )
            for i in range(rng.randint(1, 3))
        ]
        first = decode_corrections(syndromes)
        second = decode_corrections(list(reversed(syndromes)))
        assert first[0].action_id == second[0].action_id
        assert first[0].target_entity == second[0].target_entity
        assert first[0].status == second[0].status


def test_empty_syndromes_yield_no_actions():
    assert decode_corrections([]) == []
