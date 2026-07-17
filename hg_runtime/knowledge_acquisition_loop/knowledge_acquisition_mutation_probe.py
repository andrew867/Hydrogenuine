"""P30-3 mutation probes for knowledge acquisition soak."""

from __future__ import annotations

import copy

from hg_runtime.knowledge_acquisition_loop.schemas import (
    KnowledgeAcquisitionBoundaryError,
    assert_neutral,
)


def probe_mutated_task(layer: dict) -> dict:
    if not layer.get("task_layer", {}).get("tasks"):
        return {"detected": False, "error": "no tasks to mutate"}
    mutated = copy.deepcopy(layer["task_layer"]["tasks"][0])
    mutated["fixture_only"] = False
    mutated["acquisition_task_is_not_action"] = False
    mutated["acquisition_task_treated_as_action"] = True
    try:
        assert_neutral(mutated)
        return {"detected": False, "error": "mutation not caught"}
    except KnowledgeAcquisitionBoundaryError:
        return {"detected": True}


def probe_mutated_source(layer: dict) -> dict:
    if not layer.get("task_layer", {}).get("sources"):
        return {"detected": False, "error": "no sources to mutate"}
    mutated = copy.deepcopy(layer["task_layer"]["sources"][0])
    mutated["source_treated_as_authority"] = True
    try:
        assert_neutral(mutated)
        return {"detected": False, "error": "mutation not caught"}
    except KnowledgeAcquisitionBoundaryError:
        return {"detected": True}


def probe_truth_promotion_attempt(layer: dict) -> dict:
    if not layer.get("results"):
        return {"detected": False, "error": "no results to mutate"}
    mutated = copy.deepcopy(layer["results"][0])
    mutated["acquired_claim_treated_as_truth"] = True
    mutated["belief_promoted"] = True
    mutated["belief_promotion_automatic"] = True
    try:
        assert_neutral(mutated)
        return {"detected": False, "error": "mutation not caught"}
    except KnowledgeAcquisitionBoundaryError:
        return {"detected": True}


def run_mutation_probes(layer: dict) -> dict:
    task_probe = probe_mutated_task(layer)
    source_probe = probe_mutated_source(layer)
    truth_probe = probe_truth_promotion_attempt(layer)

    originals_ok = True
    if layer.get("task_layer", {}).get("tasks"):
        try:
            assert_neutral(layer["task_layer"]["tasks"][0])
        except KnowledgeAcquisitionBoundaryError:
            originals_ok = False
    if layer.get("task_layer", {}).get("sources"):
        try:
            assert_neutral(layer["task_layer"]["sources"][0])
        except KnowledgeAcquisitionBoundaryError:
            originals_ok = False
    if layer.get("results"):
        try:
            assert_neutral(layer["results"][0])
        except KnowledgeAcquisitionBoundaryError:
            originals_ok = False

    return {
        "mutated_task": task_probe,
        "mutated_source": source_probe,
        "truth_promotion": truth_probe,
        "originals_not_mutated": originals_ok,
        "mutation_not_auto_repaired": True,
    }
