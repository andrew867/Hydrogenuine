"""LEB-6 AIS integration over local evidence receipts.

Runs AIS record-health, quarantine, fever, defensive-security, and patch-hygiene
checks over local evidence receipts. Creates findings only: it does not patch,
does not delete, does not auto-quarantine beyond metadata records, and does not
mark evidence true. Local evidence remains non-authoritative.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.evidence_fever_hooks import build_evidence_fever_report
from hg_runtime.local_evidence_bridge.evidence_health_scan import build_evidence_health_findings
from hg_runtime.local_evidence_bridge.evidence_quarantine_hooks import build_evidence_quarantine_candidates
from hg_runtime.local_evidence_bridge.evidence_security_hooks import build_evidence_security_findings
from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    assert_neutral,
    neutral_flags,
    record_hash,
)

VERDICT_GREEN = "GREEN_LEB_6_AIS_INTEGRATION"
VERDICT_RED = "RED_LEB_6_AIS_INTEGRATION_FAILED"


def build_evidence_patch_hygiene_task(*, task_id: str, security_finding: dict) -> dict:
    task = {
        "schema_version": "1",
        "record_type": "evidence_patch_hygiene_task_v1",
        "task_id": task_id,
        "source_finding_id": security_finding["finding_id"],
        "finding_type": security_finding["finding_type"],
        "requested_scope": security_finding["surface"],
        "patch_hygiene_task_is_patch": False,
        "automatic_patching": False,
        "operator_approval_required": True,
        "rollback_plan_required": True,
        "live_mutation_performed": False,
        **neutral_flags(),
    }
    task["record_hash"] = record_hash(task)
    assert_neutral(task)
    return task


def build_evidence_patch_hygiene_tasks(security_findings: list[dict]) -> list[dict]:
    return [
        build_evidence_patch_hygiene_task(task_id=f"evph-{i:03d}", security_finding=f)
        for i, f in enumerate(security_findings, start=1)
    ]


def build_fixture_receipts(root) -> list[dict]:
    """Deterministic receipts: two clean fixture receipts plus a redaction-flagged one."""
    from hg_runtime.local_evidence_bridge.text_ingestion import ingest_text_source

    paths = ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_002.txt"]
    receipts = [ingest_text_source(root, p, source_id=f"src-{i}")["evidence_receipt"] for i, p in enumerate(paths, start=1)]
    flagged = dict(receipts[0])
    flagged["receipt_id"] = "ev-redaction-flagged"
    flagged["secret_like_content_redacted"] = True
    flagged["receipt_hash"] = record_hash({k: v for k, v in flagged.items() if k != "receipt_hash"})
    return [*receipts, flagged]


def build_ais_integration(root) -> dict:
    receipts = build_fixture_receipts(root)
    health = build_evidence_health_findings(receipts)
    quarantine = build_evidence_quarantine_candidates(receipts)
    fever = build_evidence_fever_report(health)
    security = build_evidence_security_findings(receipts)
    patch_tasks = build_evidence_patch_hygiene_tasks(security)

    manifest = {
        "schema_version": "1",
        "record_type": "ais_integration_manifest_v1",
        "manifest_id": "leb6-ais-integration-manifest",
        "evidence_receipt_count": len(receipts),
        "health_finding_count": len(health),
        "quarantine_candidate_count": len(quarantine),
        "security_finding_count": len(security),
        "patch_hygiene_task_count": len(patch_tasks),
        "fever_level": fever["fever_level"],
        "fever_restricts": fever["fever_restricts"],
        "health_finding_hashes": [f["record_hash"] for f in health],
        "quarantine_candidate_hashes": [q["record_hash"] for q in quarantine],
        "security_finding_hashes": [s["record_hash"] for s in security],
        "patch_hygiene_task_hashes": [t["record_hash"] for t in patch_tasks],
        "fever_report_hash": fever["record_hash"],
        "ais_finding_is_authority": False,
        "quarantine_candidate_is_deletion": False,
        "fever_unlocks_action": False,
        "security_finding_defensive_only": True,
        "patch_hygiene_task_is_patch": False,
        "local_evidence_is_authoritative": False,
        "auto_quarantine_enforced": False,
        "automatic_patching_enabled": False,
        "deletion_performed": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)

    replay = replay_ais_integration(health, quarantine, security, patch_tasks, fever, manifest)
    return {
        "receipts": receipts,
        "health": health,
        "quarantine": quarantine,
        "fever": fever,
        "security": security,
        "patch_tasks": patch_tasks,
        "manifest": manifest,
        "replay": replay,
    }


def replay_ais_integration(health, quarantine, security, patch_tasks, fever, manifest) -> dict:
    failures: list[str] = []
    checks = [
        ([f["record_hash"] for f in health], manifest.get("health_finding_hashes", []), "health_hash_mismatch"),
        ([q["record_hash"] for q in quarantine], manifest.get("quarantine_candidate_hashes", []), "quarantine_hash_mismatch"),
        ([s["record_hash"] for s in security], manifest.get("security_finding_hashes", []), "security_hash_mismatch"),
        ([t["record_hash"] for t in patch_tasks], manifest.get("patch_hygiene_task_hashes", []), "patch_hash_mismatch"),
    ]
    for computed, stored, label in checks:
        if computed != stored:
            failures.append(label)
    if fever["record_hash"] != manifest.get("fever_report_hash"):
        failures.append("fever_hash_mismatch")
    for record in [*health, *quarantine, *security, *patch_tasks, fever]:
        expected = record_hash({k: v for k, v in record.items() if k != "record_hash"})
        if record["record_hash"] != expected:
            failures.append(f"record_hash_mismatch:{record.get('finding_id') or record.get('quarantine_candidate_id') or record.get('task_id') or record.get('report_id')}")
    try:
        for record in [*health, *quarantine, *security, *patch_tasks, fever, manifest]:
            assert_neutral(record)
    except EvidenceBridgeError as exc:
        failures.append(f"boundary_violation:{exc}")
    return {
        "schema_version": "1",
        "record_type": "ais_integration_replay_v1",
        "replay_id": "leb6-ais-integration-replay",
        "replay_preserves_integration_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_leb6_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "health_findings_written": "health_findings_required",
        "quarantine_candidates_written": "quarantine_candidates_required",
        "fever_report_written": "fever_report_required",
        "security_findings_written": "security_findings_required",
        "patch_hygiene_tasks_written": "patch_hygiene_tasks_required",
        "ais_integration_manifest_written": "manifest_required",
        "ais_finding_not_authority": "finding_authority_boundary",
        "quarantine_candidate_not_deletion": "quarantine_deletion_boundary",
        "fever_restricts_never_unlocks": "fever_unlock_boundary",
        "security_finding_defensive_only": "security_defensive_boundary",
        "patch_hygiene_task_not_patch": "patch_task_boundary",
        "local_evidence_non_authoritative": "local_evidence_authority_boundary",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_deletion": "deletion_forbidden",
        "no_auto_quarantine_enforcement": "auto_quarantine_forbidden",
        "replay_preserves_integration_hashes": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "evidence_treated_as_truth",
        "ais_finding_treated_as_authority",
        "automatic_patching_enabled",
        "deletion_performed",
        "auto_quarantine_enforced",
        "fever_unlocks_action",
        "offensive_capability",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "tools_authorized",
        "authority_granted",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
