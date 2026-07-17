"""Local Inference QA Orchestrator replay."""

from __future__ import annotations

from hg_runtime.local_inference_qa_orchestrator.artifact_writer import build_qa_artifacts
from hg_runtime.local_inference_qa_orchestrator.orchestrator import run_qa_orchestrator
from hg_runtime.local_inference_qa_orchestrator.schemas import _stable_hash


def replay_qa_artifacts(model_responses: dict[str, str] | None = None) -> dict:
    return build_qa_artifacts(run_qa_orchestrator(model_responses=model_responses))


def verify_replay_hashes(run1: dict, run2: dict) -> dict:
    match = run1.get("artifact_hash") == run2.get("artifact_hash")
    return {
        "hashes_match": match,
        "run1_hash": run1.get("artifact_hash"),
        "run2_hash": run2.get("artifact_hash"),
    }


def reject_mutation(original: dict, mutated: dict) -> dict:
    h1 = _stable_hash(original)
    h2 = _stable_hash(mutated)
    return {
        "mutation_detected": h1 != h2,
        "original_hash": h1,
        "mutated_hash": h2,
    }
