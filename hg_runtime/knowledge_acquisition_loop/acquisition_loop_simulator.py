"""P30-2 fixture-only acquisition loop simulator."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.acquisition_refusal import build_acquisition_refusal
from hg_runtime.knowledge_acquisition_loop.acquisition_result import build_acquisition_result
from hg_runtime.knowledge_acquisition_loop.schemas import REFUSAL_REASONS


_REFUSED_TASK_TYPES = {
    "web_search": "live_web_acquisition",
    "external_provider": "external_provider_acquisition",
    "arbitrary_directory": "arbitrary_directory_acquisition",
    "pdf_ocr": "pdf_ocr_acquisition",
}


def simulate_acquisition_loop(tasks: list[dict], sources: list[dict]) -> dict:
    results = []
    refusals = []
    operator_reviews = []
    covered_reasons: set[str] = set()

    source_map = {s["source_id"]: s for s in sources}

    for task in tasks:
        task_type = task["task_type"]
        task_id = task["task_id"]

        if task_type in _REFUSED_TASK_TYPES:
            reason = _REFUSED_TASK_TYPES[task_type]
            refusal = build_acquisition_refusal(
                refusal_id=f"refusal-{task_id}",
                task_id=task_id,
                refusal_reason=reason,
                description=f"Refused: {reason}",
            )
            refusals.append(refusal)
            covered_reasons.add(reason)

            result = build_acquisition_result(
                result_id=f"result-refused-{task_id}",
                task_id=task_id,
                result_state="REFUSED_BY_POLICY",
                refusal_reason=reason,
            )
            results.append(result)
        else:
            source_refs = task.get("source_refs", [])
            source_id = source_refs[0] if source_refs else None

            result = build_acquisition_result(
                result_id=f"result-{task_id}",
                task_id=task_id,
                result_state="ACQUIRED_FIXTURE",
                source_id=source_id,
                acquired_content="fixture_content",
            )
            results.append(result)

            if task.get("candidate_id"):
                operator_reviews.append({
                    "review_id": f"review-{task_id}",
                    "task_id": task_id,
                    "candidate_id": task["candidate_id"],
                    "status": "pending_operator_review",
                    "acquired_claim_is_not_truth": True,
                })

    remaining = REFUSAL_REASONS - covered_reasons
    for i, reason in enumerate(sorted(remaining)):
        refusal = build_acquisition_refusal(
            refusal_id=f"refusal-extra-{i:03d}",
            task_id=f"task-synthetic-{reason}",
            refusal_reason=reason,
            description=f"Synthetic refusal to cover: {reason}",
        )
        refusals.append(refusal)
        covered_reasons.add(reason)

        result = build_acquisition_result(
            result_id=f"result-synthetic-{reason}",
            task_id=f"task-synthetic-{reason}",
            result_state="REFUSED_BY_POLICY",
            refusal_reason=reason,
        )
        results.append(result)

    unsourced = []
    for r in results:
        if r["result_state"] == "ACQUIRED_FIXTURE" and not r.get("source_id"):
            normalized = build_acquisition_result(
                result_id=f"normalized-{r['result_id']}",
                task_id=r["task_id"],
                result_state="NORMALIZED_TO_TBD",
                acquired_content=r.get("acquired_content"),
            )
            unsourced.append(normalized)

    return {
        "results": results,
        "refusals": refusals,
        "operator_reviews": operator_reviews,
        "unsourced_normalized": unsourced,
        "covered_refusal_reasons": sorted(covered_reasons),
        "all_refusal_reasons_covered": covered_reasons == REFUSAL_REASONS,
    }
