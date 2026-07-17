"""Scan boundary_assertions.json in proof bundles for forgery and laundering."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_immune_system.finding import build_finding

REQUIRED_TRUE_ASSERTIONS = frozenset({
    "phase19_yellow_preserved",
    "phase24_infrastructure_only_preserved",
    "no_live_effects",
    "no_tool_authorization",
    "no_external_provider_calls",
    "no_hg_local_access",
})

REQUIRED_FALSE_ASSERTIONS = frozenset({
    "model_output_treated_as_truth",
    "local_inference_treated_as_authority",
    "recommendations_treated_as_permission",
    "proof_bundle_existence_treated_as_truth",
    "proof_bundle_existence_treated_as_authority",
    "tools_authorized",
    "live_effects_created",
    "external_provider_calls_made",
    "remote_llm_calls_made",
    "hg_local_touched",
    "deployment_permission_claimed",
    "agi_claim_made",
})

LAUNDERING_PANIC_KEYS = frozenset({
    "deployment_permission_claimed",
    "agi_claim_made",
    "consciousness_claim_made",
    "sovereignty_claim_made",
})


def scan_boundary_assertions(bundle_dir: Path) -> list[dict]:
    findings: list[dict] = []
    bundle_dir = Path(bundle_dir)
    label = bundle_dir.name
    ba_path = bundle_dir / "boundary_assertions.json"
    gate_path = bundle_dir / "gate_result.json"

    if not gate_path.exists():
        return findings

    if not ba_path.exists():
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-missing-boundary-assertions",
                finding_type="missing_boundary_assertions",
                severity="YELLOW",
                safe_action="REQUEST_EVIDENCE",
                surface=str(ba_path),
                blocks_green=False,
            )
        )
        return findings

    try:
        data = json.loads(ba_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-malformed-boundary-assertions",
                finding_type="malformed_boundary_assertions",
                severity="RED",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(ba_path),
                blocks_green=True,
            )
        )
        return findings

    if not isinstance(data, dict):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-malformed-boundary-assertions",
                finding_type="malformed_boundary_assertions",
                severity="RED",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(ba_path),
                blocks_green=True,
            )
        )
        return findings

    for key in REQUIRED_TRUE_ASSERTIONS:
        val = data.get(key)
        if val is None:
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-ba-missing-{key}",
                    finding_type="boundary_assertion_missing_required",
                    severity="YELLOW",
                    safe_action="REQUEST_EVIDENCE",
                    surface=str(ba_path),
                    extra={"assertion_key": key, "expected": True},
                )
            )
        elif val is not True:
            severity = "PANIC" if key.startswith("phase") else "RED"
            finding_type = (
                "boundary_assertion_phase_laundering"
                if key.startswith("phase")
                else "boundary_assertion_safety_violation"
            )
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-ba-violated-{key}",
                    finding_type=finding_type,
                    severity=severity,
                    safe_action="RESTRICT",
                    surface=str(ba_path),
                    blocks_green=True,
                    extra={"assertion_key": key, "expected": True, "actual": val},
                )
            )

    for key in REQUIRED_FALSE_ASSERTIONS:
        val = data.get(key)
        if val is None:
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-ba-missing-{key}",
                    finding_type="boundary_assertion_missing_required",
                    severity="YELLOW",
                    safe_action="REQUEST_EVIDENCE",
                    surface=str(ba_path),
                    extra={"assertion_key": key, "expected": False},
                )
            )
        elif val is not False:
            if key in LAUNDERING_PANIC_KEYS:
                severity = "PANIC"
                finding_type = "boundary_assertion_laundering_claim"
            else:
                severity = "RED"
                finding_type = "boundary_assertion_safety_violation"
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-ba-violated-{key}",
                    finding_type=finding_type,
                    severity=severity,
                    safe_action="RESTRICT",
                    surface=str(ba_path),
                    blocks_green=True,
                    extra={"assertion_key": key, "expected": False, "actual": val},
                )
            )

    return findings
