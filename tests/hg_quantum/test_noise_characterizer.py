from __future__ import annotations

from hg_quantum.noise_model.noise_characterizer import NoiseCharacterizer
from hg_quantum.noise_model.tlf_detector import detect_tlf_noise


def test_detect_tlf_context_overflow():
    src = detect_tlf_noise("ent1", [{"token_count": 120000}])
    assert src is not None
    assert src.source_type == "context_overflow"


def test_characterize_ranks_sources():
    char = NoiseCharacterizer()
    result = char.characterize(
        "ent1",
        [{"token_count": 120000}, {"emotional_delta": 0.5}, {"emotional_delta": 0.6}],
    )
    assert result.sources
    assert result.overall_snr < 1.0


def test_compute_noise_budget_per_entity():
    char = NoiseCharacterizer()
    budgets = char.compute_noise_budget(
        {"stages": ["plan", "verify"], "noise_budget_total": 1.0},
        ["e1", "e2"],
        observations_by_entity={"e1": [{"token_count": 120000}]},
    )
    assert "e1" in budgets
    assert budgets["e1"].total_budget <= 1.0
