"""Research continuation gate — GREEN if continuation policy ran."""

from __future__ import annotations

from hg_runtime.research_continuation.continuation_policy import CONTINUATION_DECISIONS

VERDICT_GREEN = "GREEN_RESEARCH_CONTINUATION_READY"
VERDICT_RED = "RED_RESEARCH_CONTINUATION_FAILED"


def evaluate_gate(proposals: list[dict]) -> dict:
    if not proposals:
        return {
            "verdict": VERDICT_RED,
            "reason": "no_proposals_evaluated",
            "proposal_count": 0,
            "failures": ["no_proposals_evaluated"],
        }

    failures = []
    for i, p in enumerate(proposals):
        if p.get("decision") not in CONTINUATION_DECISIONS:
            failures.append(f"proposal[{i}]: unknown decision {p.get('decision')}")
        if p.get("proposal_grants_authority"):
            failures.append(f"proposal[{i}]: proposal_grants_authority is True")
        if p.get("proposal_promotes_to_truth"):
            failures.append(f"proposal[{i}]: proposal_promotes_to_truth is True")

    continue_count = sum(1 for p in proposals if p.get("decision", "").startswith("CONTINUE"))
    drop_count = sum(1 for p in proposals if p.get("decision", "").startswith("DROP"))
    hold_count = sum(1 for p in proposals if p.get("decision", "").startswith("HOLD"))

    verdict = VERDICT_GREEN if not failures else VERDICT_RED
    return {
        "verdict": verdict,
        "reason": "continuation_policy_ran" if not failures else "; ".join(failures[:5]),
        "proposal_count": len(proposals),
        "continue_count": continue_count,
        "drop_count": drop_count,
        "hold_count": hold_count,
        "failures": failures,
    }
