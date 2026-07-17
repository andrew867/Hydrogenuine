"""AIS-5 cruft and decay manager."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS, CRUFT_CLASSIFICATIONS, assert_neutral, neutral_flags


def cruft_decay_fixtures() -> list[tuple[str, str, str, str]]:
    return [
        ("cd-stale-proof", "stale_proof_bundle", "docs/proofs/autonomous_agent_zero/OLD", "REVIEW"),
        ("cd-stale-report", "stale_report", "docs/reports/phases/OLD_REPORT.md", "REVIEW"),
        ("cd-obsolete-doc", "obsolete_doc", "docs/obsolete.md", "ARCHIVE"),
        ("cd-abandoned-todo", "abandoned_todo", "hg_runtime/fixture/todo.py", "REVIEW"),
        ("cd-orphan-fixture", "unreferenced_fixture", "fixtures/orphan.json", "ARCHIVE"),
        ("cd-old-snapshot", "old_snapshot_unreachable", "docs/proofs/snapshot.json", "ARCHIVE"),
        ("cd-expired-assumption", "expired_assumption", "docs/planning/assumption.md", "REVIEW"),
        ("cd-old-yellow", "old_yellow_state_needs_review", "docs/proofs/phase19", "KEEP"),
        ("cd-long-quarantine", "long_lived_quarantine_item", "docs/proofs/quarantine", "QUARANTINE"),
        ("cd-remove-candidate", "remove_candidate_requires_operator", "fixtures/remove_candidate", "REMOVE_CANDIDATE"),
    ]


def build_cruft_decay_finding(
    *, finding_id: str, finding_type: str, surface: str, classification: str
) -> dict:
    if classification not in CRUFT_CLASSIFICATIONS:
        raise ValueError(f"invalid_cruft_classification:{classification}")
    finding = {
        "schema_version": "1",
        "record_type": "cruft_decay_finding_v1",
        "finding_id": finding_id,
        "finding_type": finding_type,
        "surface": surface,
        "classification": classification,
        "maintenance_task": f"review:{finding_id}",
        "decay_is_not_deletion": True,
        "archive_is_not_erasure": True,
        "stale_is_not_false": True,
        "remove_candidate_is_not_removal_permission": True,
        "operator_approval_required_for_removal": True,
        "proof_bundles_preserved": True,
        "deletion_performed": False,
        "archive_performed": False,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_cruft_decay_layer() -> dict:
    findings = [
        build_cruft_decay_finding(
            finding_id=finding_id,
            finding_type=finding_type,
            surface=surface,
            classification=classification,
        )
        for finding_id, finding_type, surface, classification in cruft_decay_fixtures()
    ]
    manifest = {
        "schema_version": "1",
        "record_type": "cruft_decay_manifest_v1",
        "manifest_id": "ais5-cruft-decay-manager",
        "finding_count": len(findings),
        "finding_types": sorted({f["finding_type"] for f in findings}),
        "classifications": sorted({f["classification"] for f in findings}),
        "finding_hashes": [f["record_hash"] for f in findings],
        "decay_is_not_deletion": True,
        "archive_is_not_erasure": True,
        "operator_approval_required_for_removal": True,
        "proof_bundles_preserved": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    replay = replay_cruft_decay_layer(findings, manifest)
    return {"findings": findings, "manifest": manifest, "replay": replay}


def replay_cruft_decay_layer(findings: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [f["record_hash"] for f in findings] != manifest.get("finding_hashes", []):
        failures.append("finding_hash_list_mismatch")
    for finding in findings:
        assert_neutral(finding)
        expected = record_hash({k: v for k, v in finding.items() if k != "record_hash"})
        if finding["record_hash"] != expected:
            failures.append(f"finding_hash_mismatch:{finding['finding_id']}")
    return {
        "schema_version": "1",
        "record_type": "cruft_decay_replay_record_v1",
        "replay_id": "ais5-cruft-decay-replay",
        "replay_preserves_decay_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_cruft_decay_finding(finding: dict) -> None:
    assert_neutral(finding)
    if finding.get("deletion_performed"):
        raise ValueError("decay_cannot_delete")
    if finding.get("archive_performed"):
        raise ValueError("archive_is_not_performed_by_ais5")
    if not finding.get("remove_candidate_is_not_removal_permission"):
        raise ValueError("remove_candidate_boundary_required")
