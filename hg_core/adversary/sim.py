"""
Pack 5: Attacker simulation harness — deterministic scenarios, expected enforcement.
ATTACK_SIMULATION_STARTED, ATTACK_SIMULATION_COMPLETED, ATTACK_SCENARIO_FAILED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hg_core.ledger import emit


SCENARIO_NAMES = ("cheap_green_light", "correlated_outage", "slow_truth", "receipt_forgery")


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_adversarial_ledger(workspace_root: Path, scenario: str, run_id: str, events: List[Dict[str, Any]]) -> Path:
    """Write deterministic adversarial ledger (artifact)."""
    root = workspace_root / "artifacts" / "adversary" / "runs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}_{scenario}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return path


def run_attack_scenario(
    scenario: str,
    workspace_root: Path,
    *,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    gate_checker: Optional[Callable[[Path, str], Tuple[bool, str]]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Run one attacker scenario deterministically. Returns (passed, result_dict).
    passed=True means system correctly refused commit or waited; passed=False means ATTACK_SCENARIO_FAILED.
    gate_checker(workspace_root, action_id) -> (allowed_commit, reason). If None, we only build ledger and assume no commit.
    """
    workspace_root = Path(workspace_root)
    scope = scope or {"type": "run", "id": "adversary_sim"}
    actor = actor or {"agent_id": "adversary_sim", "pubkey": "", "key_id": ""}
    ts = _iso_ts()
    run_id = "asim_" + hashlib.sha256(f"{scenario}:{ts}".encode()).hexdigest()[:16]

    emit(
        "ATTACK_SIMULATION_STARTED",
        "attack_simulation",
        run_id,
        {"run_id": run_id, "scenario": scenario, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )

    events: List[Dict[str, Any]] = []
    action_id = f"act_{scenario}_{run_id[:8]}"
    committed_incorrectly = False
    summary: Dict[str, Any] = {"scenario": scenario, "run_id": run_id, "expected_block": True, "committed": False}

    if scenario == "cheap_green_light":
        # Cheap verifier passes, independent would fail. System must not allow commit without independent confirmation.
        events.append({"event": "verification_check", "source_id": "cheap_source", "result": "pass", "action_id": action_id})
        events.append({"event": "verification_check", "source_id": "independent_source", "result": "fail", "action_id": action_id})
        if gate_checker:
            allowed, reason = gate_checker(workspace_root, action_id)
            if allowed:
                committed_incorrectly = True
                summary["committed"] = True
                summary["reason"] = reason
        else:
            summary["committed"] = False

    elif scenario == "correlated_outage":
        # Multiple verifiers fail together (same cluster).
        for sid in ["src_a", "src_b", "src_c"]:
            events.append({"event": "verification_check", "source_id": sid, "result": "fail", "action_id": action_id})
        if gate_checker:
            allowed, _ = gate_checker(workspace_root, action_id)
            if allowed:
                committed_incorrectly = True
                summary["committed"] = True
        else:
            summary["committed"] = False

    elif scenario == "slow_truth":
        # Verification arrives after commit attempt; system must wait. We don't model time order in ledger here; outcome = "wait".
        events.append({"event": "commit_attempt", "action_id": action_id, "ts": ts})
        events.append({"event": "verification_check", "source_id": "delayed_source", "result": "pass", "action_id": action_id})
        summary["expected_block"] = False
        summary["expected_wait"] = True

    elif scenario == "receipt_forgery":
        # Tool receipt says success, independent observation contradicts -> block and raise incident candidate.
        events.append({"event": "tool_receipt", "action_id": action_id, "claimed_result": "success"})
        events.append({"event": "verification_check", "source_id": "independent_observer", "result": "fail", "action_id": action_id})
        if gate_checker:
            allowed, reason = gate_checker(workspace_root, action_id)
            if allowed:
                committed_incorrectly = True
                summary["committed"] = True
                summary["reason"] = reason
        else:
            summary["committed"] = False
        summary["incident_candidate_expected"] = True

    else:
        summary["error"] = f"unknown_scenario_{scenario}"
        committed_incorrectly = False

    ledger_path = _write_adversarial_ledger(workspace_root, scenario, run_id, events)
    summary["ledger_artifact_id"] = str(ledger_path)
    summary["ts"] = _iso_ts()

    if committed_incorrectly:
        emit(
            "ATTACK_SCENARIO_FAILED",
            "attack_simulation",
            run_id,
            {"run_id": run_id, "scenario": scenario, "action_id": action_id, "summary": summary, "ts": summary["ts"]},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )

    emit(
        "ATTACK_SIMULATION_COMPLETED",
        "attack_simulation",
        run_id,
        {"run_id": run_id, "scenario": scenario, "summary_artifact_id": str(ledger_path), "passed": not committed_incorrectly, "ts": summary["ts"]},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )

    return (not committed_incorrectly), summary


def run_all_scenarios(
    workspace_root: Path,
    *,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    gate_checker: Optional[Callable[[Path, str], Tuple[bool, str]]] = None,
    scenarios: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run all (or given) scenarios. Returns aggregate result for regression suite.
    """
    scenarios = scenarios or list(SCENARIO_NAMES)
    results: Dict[str, Any] = {"passed": [], "failed": [], "summaries": {}}
    for name in scenarios:
        if name not in SCENARIO_NAMES:
            continue
        passed, summary = run_attack_scenario(name, workspace_root, scope=scope, actor=actor, gate_checker=gate_checker)
        results["summaries"][name] = summary
        if passed:
            results["passed"].append(name)
        else:
            results["failed"].append(name)
    results["all_passed"] = len(results["failed"]) == 0
    return results
