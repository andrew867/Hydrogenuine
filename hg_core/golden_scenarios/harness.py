"""Golden scenario harness orchestration (CT-14 GLD)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.golden_scenarios.manifest import GoldenScenario, GoldenScenariosManifest, load_manifest
from hg_core.golden_scenarios.runners import get_runner


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    status: str
    terminal_state: str
    expected_terminal_state: str
    passed: bool
    skipped: bool
    skip_reason: str
    narrative: tuple[str, ...]
    event_types: tuple[str, ...]
    artifacts: dict[str, Any]
    proof_bundle_ref: str | None
    replay_hash: str | None
    deterministic: bool
    error: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "status": self.status,
            "terminal_state": self.terminal_state,
            "expected_terminal_state": self.expected_terminal_state,
            "passed": self.passed,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "narrative": list(self.narrative),
            "event_types": list(self.event_types),
            "artifacts": self.artifacts,
            "proof_bundle_ref": self.proof_bundle_ref,
            "replay_hash": self.replay_hash,
            "deterministic": self.deterministic,
            "error": self.error,
        }


def _should_skip(spec: GoldenScenario) -> tuple[bool, str]:
    if spec.skip_default:
        return True, spec.skip_reason or "skip_default"
    if spec.requires_live and os.environ.get("HG_RTC_COGNITION_LIVE", "").strip() != "1":
        return True, "requires_live_provider"
    return False, ""


def run_scenario(
    spec: GoldenScenario,
    *,
    workspace: Path | None = None,
) -> ScenarioResult:
    root = workspace or Path(__file__).resolve().parents[2]
    skipped, skip_reason = _should_skip(spec)
    if skipped:
        return ScenarioResult(
            scenario_id=spec.scenario_id,
            status="skipped",
            terminal_state="skipped",
            expected_terminal_state=spec.expected_terminal_state,
            passed=True,
            skipped=True,
            skip_reason=skip_reason,
            narrative=(f"Skipped: {skip_reason}",),
            event_types=(),
            artifacts={},
            proof_bundle_ref=spec.proof_bundle_ref,
            replay_hash=None,
            deterministic=spec.deterministic,
        )
    try:
        raw = get_runner(spec.runner)(spec, root)
    except Exception as exc:
        return ScenarioResult(
            scenario_id=spec.scenario_id,
            status="failed",
            terminal_state="error",
            expected_terminal_state=spec.expected_terminal_state,
            passed=False,
            skipped=False,
            skip_reason="",
            narrative=(f"Runner error: {exc}",),
            event_types=(),
            artifacts={},
            proof_bundle_ref=spec.proof_bundle_ref,
            replay_hash=None,
            deterministic=spec.deterministic,
            error=str(exc),
        )
    terminal = str(raw.get("terminal_state", ""))
    event_types = tuple(str(x) for x in raw.get("event_types", ()))
    passed = terminal == spec.expected_terminal_state
    if spec.expected_events:
        missing = [e for e in spec.expected_events if e not in event_types]
        if missing:
            passed = False
    if raw.get("error") == "missing_proof_bundle":
        passed = False
    return ScenarioResult(
        scenario_id=spec.scenario_id,
        status="passed" if passed else "failed",
        terminal_state=terminal,
        expected_terminal_state=spec.expected_terminal_state,
        passed=passed,
        skipped=False,
        skip_reason="",
        narrative=tuple(str(x) for x in raw.get("narrative", ())),
        event_types=event_types,
        artifacts=dict(raw.get("artifacts", {})),
        proof_bundle_ref=raw.get("proof_bundle_ref", spec.proof_bundle_ref),
        replay_hash=raw.get("replay_hash"),
        deterministic=spec.deterministic,
        error=str(raw.get("error", "")),
    )


def run_all_scenarios(
    *,
    workspace: Path | None = None,
    manifest: GoldenScenariosManifest | None = None,
) -> list[ScenarioResult]:
    loaded = manifest or load_manifest(workspace=workspace)
    return [run_scenario(spec, workspace=workspace) for spec in loaded.scenarios]


def narrative_trace(results: list[ScenarioResult]) -> dict[str, Any]:
    return {
        item.scenario_id: {
            "status": item.status,
            "narrative": list(item.narrative),
            "terminal_state": item.terminal_state,
        }
        for item in results
    }


__all__ = ["ScenarioResult", "narrative_trace", "run_all_scenarios", "run_scenario"]
