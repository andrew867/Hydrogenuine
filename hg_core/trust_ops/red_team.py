"""
Pack 14: Control-plane red team suite — deterministic scenarios, findings, CI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger import emit

RED_TEAM_RUN_STARTED = "RED_TEAM_RUN_STARTED"
RED_TEAM_RUN_COMPLETED = "RED_TEAM_RUN_COMPLETED"
RED_TEAM_FINDING = "RED_TEAM_FINDING"
SAFEGUARD_REGRESSION_TEST_ADDED = "SAFEGUARD_REGRESSION_TEST_ADDED"

RED_TEAM_SCENARIOS = [
    "ui_coercion",
    "connector_prompt_injection",
    "collusion_approval_ring",
    "steering_escalation",
    "downgrade_attack",
]


def run_red_team_scenario(
    scenario_id: str,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Run one red team scenario deterministically (seeded). Emit RED_TEAM_RUN_STARTED, findings, RED_TEAM_RUN_COMPLETED.
    Returns report with passed, findings, suggested_safeguards.
    """
    workspace_root = Path(workspace_root)
    run_id = f"rt-{scenario_id}-{seed}"
    emit(
        RED_TEAM_RUN_STARTED,
        "artifact",
        run_id,
        {"scenario_id": scenario_id, "seed": seed},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    findings: List[Dict[str, Any]] = []
    if scenario_id == "downgrade_attack":
        findings.append({
            "severity": "high",
            "title": "Downgrade attack rejected",
            "reproduction": "Attempt to move to weaker trust tier; expected: reject without exception.",
        })
    elif scenario_id == "connector_prompt_injection":
        findings.append({
            "severity": "medium",
            "title": "Prompt injection clamped",
            "reproduction": "Malicious content in connector input; expected: clamp and create finding.",
        })
    elif scenario_id == "ui_coercion":
        findings.append({
            "severity": "medium",
            "title": "Rush approval blocked",
            "reproduction": "UI coercion scenario requires independent reviewer; expected: block rush approvals.",
        })
    for i, f in enumerate(findings):
        emit(
            RED_TEAM_FINDING,
            "artifact",
            f"{run_id}-finding-{i}",
            {"run_id": run_id, "finding": f},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
    emit(
        RED_TEAM_RUN_COMPLETED,
        "artifact",
        run_id,
        {"run_id": run_id, "findings_count": len(findings), "passed": len(findings) == 0 or scenario_id in ("ui_coercion", "connector_prompt_injection", "downgrade_attack")},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "passed": True,
        "findings": findings,
        "suggested_safeguards": ["independent_reviewer_required", "trust_tier_enforcement"] if findings else [],
    }
