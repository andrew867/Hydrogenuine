"""Parse soak results for pass/fail/flake summaries."""

from __future__ import annotations

from collections import defaultdict


def summarize_results(soak: dict) -> dict:
    results = soak["all_results"]
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"] and not r.get("rejected") and not r.get("timed_out"))
    rejected = sum(1 for r in results if r.get("rejected"))
    timed_out = sum(1 for r in results if r.get("timed_out"))

    optional_missing = soak.get("optional_missing", [])
    optional_missing_count = len(optional_missing)
    substitute_passed = all(
        any(
            r["command"] == om["substitute"] and r["passed"]
            for r in results
        )
        for om in optional_missing
    ) if optional_missing else False

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "rejected": rejected,
        "timed_out": timed_out,
        "all_passed": failed == 0 and rejected == 0 and timed_out == 0,
        "optional_missing_count": optional_missing_count,
        "substitute_passed": substitute_passed,
        "optional_missing": optional_missing,
    }


def detect_flakes(soak: dict) -> list[dict]:
    cmd_results: dict[str, list[bool]] = defaultdict(list)
    for r in soak["all_results"]:
        if r.get("rejected") or r.get("timed_out"):
            continue
        cmd_results[r["command"]].append(r["passed"])

    flakes = []
    for cmd, outcomes in cmd_results.items():
        if len(outcomes) < 2:
            continue
        passed = sum(1 for o in outcomes if o)
        failed = sum(1 for o in outcomes if not o)
        if passed > 0 and failed > 0:
            flakes.append({
                "command": cmd,
                "total_runs": len(outcomes),
                "passed": passed,
                "failed": failed,
                "flake_rate": round(min(passed, failed) / len(outcomes), 3),
            })

    return flakes
