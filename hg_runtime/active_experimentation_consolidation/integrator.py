"""AEC-06 / CAGI-53 integrator — validates cross-phase AEC integration."""

from __future__ import annotations

from hg_runtime.active_experimentation_consolidation.schemas import (
    AEC_PHASES,
    ConsolidationError,
    reject_completion_claim,
)


def validate_phase_verdicts(verdicts: dict) -> list[str]:
    issues = []
    for phase in AEC_PHASES[:-1]:
        verdict = verdicts.get(phase, "")
        if not verdict.startswith("GREEN"):
            issues.append(f"{phase}_not_green")
    return issues


def validate_integration_checks(checks: list[dict]) -> list[str]:
    issues = []
    for check in checks:
        if not check.get("verified"):
            issues.append(f"unverified_{check.get('check_id', 'unknown')}")
    return issues


def compute_tranche_summary(stats: list[dict]) -> dict:
    total_modules = sum(s["modules"] for s in stats)
    total_tests = sum(s["tests"] for s in stats)
    return {
        "phase_count": len(stats),
        "total_modules": total_modules,
        "total_tests": total_tests,
        "packages": [s["package"] for s in stats],
    }
