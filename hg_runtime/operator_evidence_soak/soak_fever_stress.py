"""OES-3 soak health findings from mutation and replay signals."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash


def build_soak_health_finding(*, finding_id: str, signal_type: str, severity: str, evidence_ref: str) -> dict:
    finding = {
        "schema_version": "1",
        "record_type": "soak_health_finding_v1",
        "finding_id": finding_id,
        "source_component": "operator_evidence_soak",
        "signal_type": signal_type,
        "severity": severity,
        "evidence_ref": evidence_ref,
        "finding_is_authority": False,
        "soak_treated_as_truth": False,
        "replay_match_treated_as_truth": False,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_soak_health_findings(*, mutation_results: list[dict], mismatch_records: list[dict], replay_all_match: bool) -> list[dict]:
    findings = []
    if not replay_all_match:
        findings.append(
            build_soak_health_finding(
                finding_id="oes-health-replay-drift",
                signal_type="soak_replay_drift_observed",
                severity="YELLOW",
                evidence_ref="soak_replay_result",
            )
        )
    for i, mismatch in enumerate(mismatch_records, start=1):
        findings.append(
            build_soak_health_finding(
                finding_id=f"oes-health-mismatch-{i:03d}",
                signal_type="soak_mutation_mismatch_observed",
                severity="YELLOW",
                evidence_ref=mismatch.get("probe_id", f"mismatch-{i:03d}"),
            )
        )
    for i, result in enumerate(mutation_results, start=1):
        if result["mismatch_detected"]:
            continue
        findings.append(
            build_soak_health_finding(
                finding_id=f"oes-health-undetected-{i:03d}",
                signal_type="soak_mutation_undetected",
                severity="RED",
                evidence_ref=result["probe_id"],
            )
        )
    if not findings:
        findings.append(
            build_soak_health_finding(
                finding_id="oes-health-clean",
                signal_type="soak_pipeline_observed",
                severity="WATCH",
                evidence_ref="soak_baseline",
            )
        )
    return findings
