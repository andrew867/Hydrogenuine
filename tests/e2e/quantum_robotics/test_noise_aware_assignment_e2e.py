"""E2E: noise-aware task assignment across entity pool."""
from __future__ import annotations

import pytest

from hg_quantum.noise_model.noise_characterizer import NoiseCharacterizer

from .proof_writer import write_proof_bundle

pytestmark = pytest.mark.e2e_quantum_robotics


def _assign_analytical_task(char: NoiseCharacterizer, observations: dict) -> str:
    best_id = ""
    best_snr = -1.0
    for entity_id, obs in observations.items():
        result = char.characterize(entity_id, obs)
        context_noise = sum(
            s.magnitude for s in result.sources if s.source_type in ("context_overflow", "context_saturation")
        )
        if context_noise > 0.5:
            continue
        if result.overall_snr > best_snr:
            best_snr = result.overall_snr
            best_id = entity_id
    return best_id


def test_e2e_noise_aware_assignment(proof_dir):
    observations = {
        "entity_a": [{"token_count": 120_000}, {"token_count": 115_000}],
        "entity_b": [{"emotional_delta": 0.8}, {"emotional_delta": 0.7}],
        "entity_c": [{"token_count": 1000}, {"token_count": 1200}],
    }
    char = NoiseCharacterizer()
    assigned = _assign_analytical_task(char, observations)
    budgets = char.compute_noise_budget(
        {"stages": ["plan", "execute"], "noise_budget_total": 1.0},
        list(observations.keys()),
        observations_by_entity=observations,
    )

    bundle = proof_dir / "noise_aware_assignment"
    checks = [
        {"name": "assigns_low_noise_entity", "pass": assigned == "entity_c"},
        {"name": "entity_c_best_budget", "pass": budgets["entity_c"].total_budget >= budgets["entity_a"].total_budget},
    ]
    write_proof_bundle(bundle, label="e2e_noise_aware_assignment", checks=checks, summary_extra={"assigned": assigned})
    assert assigned == "entity_c"
