"""OES-3 AIS fever/quarantine stress integration over soak findings."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.evidence_fever_hooks import build_evidence_fever_report
from hg_runtime.operator_evidence_soak.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash
from hg_runtime.operator_evidence_soak.soak_fever_stress import build_soak_health_findings
from hg_runtime.operator_evidence_soak.soak_quarantine_stress import build_soak_quarantine_candidates
from hg_runtime.operator_evidence_soak.soak_security_stress import (
    build_soak_patch_hygiene_tasks,
    build_soak_security_findings,
)


def build_ais_stress_manifest(
    *,
    health_findings: list[dict],
    fever_report: dict,
    quarantine_candidates: list[dict],
    security_findings: list[dict],
    patch_hygiene_tasks: list[dict],
) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "ais_stress_manifest_v1",
        "manifest_id": "oes-ais-stress-manifest-v1",
        "health_finding_count": len(health_findings),
        "fever_report_count": 1,
        "quarantine_candidate_count": len(quarantine_candidates),
        "security_finding_count": len(security_findings),
        "patch_hygiene_task_count": len(patch_hygiene_tasks),
        "fever_level": fever_report["fever_level"],
        "fever_restricts": fever_report["fever_restricts"],
        "fever_unlocks_action": False,
        "quarantine_candidate_is_deletion": False,
        "security_finding_defensive_only": True,
        "patch_hygiene_task_is_patch": False,
        "mutation_detection_is_repair": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def run_ais_soak_stress(*, mutation_layer: dict, soak_replay: dict) -> dict:
    health = build_soak_health_findings(
        mutation_results=mutation_layer["mutation_results"],
        mismatch_records=mutation_layer["mismatch_records"],
        replay_all_match=soak_replay["soak_replay_result"]["all_iterations_match"],
    )
    fever = build_evidence_fever_report(health, report_id="oes-fever-report-001")
    quarantine = build_soak_quarantine_candidates(health)
    security = build_soak_security_findings(mismatch_records=mutation_layer["mismatch_records"])
    patch_tasks = build_soak_patch_hygiene_tasks(security)
    manifest = build_ais_stress_manifest(
        health_findings=health,
        fever_report=fever,
        quarantine_candidates=quarantine,
        security_findings=security,
        patch_hygiene_tasks=patch_tasks,
    )
    return {
        "soak_health_findings": health,
        "soak_fever_reports": [fever],
        "soak_quarantine_candidates": quarantine,
        "soak_security_findings": security,
        "soak_patch_hygiene_tasks": patch_tasks,
        "ais_stress_manifest": manifest,
    }
