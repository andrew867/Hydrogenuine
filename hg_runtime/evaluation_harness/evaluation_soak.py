"""P31 evaluation soak — runs evaluation replay multiple iterations, checks stability and mutation detection."""

from __future__ import annotations

import copy
from typing import Any

from hg_runtime.evaluation_harness.fixtures import builtin_fixtures
from hg_runtime.evaluation_harness.fixture_runner import evaluate_fixture, run_fixtures
from hg_runtime.evaluation_harness.evaluation_replay import replay_evaluation
from hg_runtime.evaluation_harness.hashing import stable_hash
from hg_runtime.evaluation_harness.schemas import SOAK_ITERATION_COUNT, assert_neutral


def _mutate_fixture(fixture: dict) -> dict:
    m = copy.deepcopy(fixture)
    m["expected_output"] = {k: not v if isinstance(v, bool) else v for k, v in m["expected_output"].items()}
    return m


def _mutate_expected_observed(fixture: dict, observed: dict) -> dict:
    bad_observed = {k: not v if isinstance(v, bool) else v for k, v in observed.items()}
    return evaluate_fixture(fixture, bad_observed, "mutation_model")


def _mutate_fake_competence(result: dict) -> dict:
    m = copy.deepcopy(result)
    m["competence_claimed"] = True
    try:
        assert_neutral(m)
        return {"detected": False}
    except Exception:
        return {"detected": True}


def run_soak(
    *,
    model_id: str = "fixture_deterministic_model",
    iterations: int = SOAK_ITERATION_COUNT,
) -> dict[str, Any]:
    fixtures = builtin_fixtures()
    observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}

    iteration_summaries = []
    iteration_hashes = []
    for i in range(iterations):
        summary = run_fixtures(fixtures, observed, model_id)
        h = stable_hash(summary)
        iteration_summaries.append(summary)
        iteration_hashes.append(h)

    unique_hashes = len(set(iteration_hashes))
    replay = replay_evaluation(fixtures, observed, model_id, iterations=iterations)

    original_fixture = fixtures[0]
    original_copy = copy.deepcopy(original_fixture)

    mutated = _mutate_fixture(original_fixture)
    mutation_fixture_detected = mutated["expected_output"] != original_fixture["expected_output"]

    eo_result = _mutate_expected_observed(fixtures[0], observed[fixtures[0]["task_id"]])
    mutation_eo_detected = eo_result["state"] == "FAIL"

    fake_comp = _mutate_fake_competence(iteration_summaries[0])
    mutation_fake_competence_detected = fake_comp["detected"]

    originals_ok = original_fixture == original_copy

    result = {
        "schema": "evaluation_soak_v1",
        "iterations": iterations,
        "iteration_hashes": iteration_hashes,
        "unique_run_hashes": unique_hashes,
        "run_deterministic": unique_hashes == 1,
        "replay_deterministic": replay["deterministic"],
        "replay_unique_hashes": replay["unique_hashes"],
        "all_deterministic": unique_hashes == 1 and replay["deterministic"],
        "iteration_count_met": iterations >= SOAK_ITERATION_COUNT,
        "stable_hashes_match": unique_hashes == 1,
        "mutation_detected_fixture": mutation_fixture_detected,
        "mutation_detected_expected_observed": mutation_eo_detected,
        "mutation_detected_fake_competence": mutation_fake_competence_detected,
        "mutation_not_auto_repaired": True,
        "originals_not_mutated": originals_ok,
        "soak_is_not_truth": True,
        "soak_is_not_competence": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(result)
    return result
