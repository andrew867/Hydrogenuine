"""Phase 37 risk-register generation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.proposal_compiler.schemas import ADVISORY_LABEL, UNKNOWN


def risk_entries(p: Mapping[str, Any]) -> list[dict[str, Any]]:
    component = str(p.get("phase_or_component") or UNKNOWN)
    pid = str(p.get("proposal_id") or UNKNOWN)
    return [
        {
            "risk_id": f"{pid}-R1",
            "risk": "Executor over-reaches and implements live external effects while repairing.",
            "phase_or_component": component,
            "severity": "HIGH",
            "likelihood": "LOW",
            "mitigation": "Spec/milestone forbid live effects; gate audits side effects.",
            "test_coverage": "dry_live_boundary_preserved",
            "residual_risk": "LOW",
        },
        {
            "risk_id": f"{pid}-R2",
            "risk": "Fix reported GREEN without real verification (fake green).",
            "phase_or_component": component,
            "severity": "HIGH",
            "likelihood": "LOW",
            "mitigation": "Gate refuses GREEN unless tests pass and replay is deterministic.",
            "test_coverage": "fake_green_rejected",
            "residual_risk": "LOW",
        },
        {
            "risk_id": f"{pid}-R3",
            "risk": "Secret material leaks into generated artifacts.",
            "phase_or_component": component,
            "severity": "MEDIUM",
            "likelihood": "LOW",
            "mitigation": "Inputs and artifacts are redacted before write.",
            "test_coverage": "secret_redaction",
            "residual_risk": "LOW",
        },
        {
            "risk_id": f"{pid}-R4",
            "risk": "Repair regresses Phase 35 / Phase 36 substrate.",
            "phase_or_component": component,
            "severity": "MEDIUM",
            "likelihood": "MEDIUM",
            "mitigation": "Substrate suites are part of acceptance.",
            "test_coverage": "integration_substrate_unregressed",
            "residual_risk": "LOW",
        },
    ]


def risk_register_update(p: Mapping[str, Any]) -> str:
    lines = [
        f"# 05 Risk Register Update — {p.get('proposal_id', UNKNOWN)}",
        "",
        f"> {ADVISORY_LABEL}.",
        "",
        "```yaml",
    ]
    for entry in risk_entries(p):
        lines.append(f"{entry['risk_id']}:")
        for key in ("risk", "phase_or_component", "severity", "likelihood", "mitigation", "test_coverage", "residual_risk"):
            lines.append(f'  {key}: "{entry[key]}"')
    lines.append("```")
    return "\n".join(lines) + "\n"


__all__ = ["risk_entries", "risk_register_update"]
