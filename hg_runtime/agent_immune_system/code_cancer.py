"""AIS-4 deterministic code cancer detector."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags

FINDING_TYPES = (
    "dead_module",
    "unused_schema",
    "duplicate_behavior_name",
    "conflicting_owner",
    "circular_dependency_candidate",
    "test_only_logic_leak",
    "mock_path_pretending_real",
    "silent_fallback_provider",
    "divergent_duplicate_gate",
    "one_behavior_many_owners",
)


def code_cancer_fixtures() -> list[dict]:
    return [
        ("cc-dead-module", "dead_module", "hg_runtime/fixture/dead_module.py"),
        ("cc-unused-schema", "unused_schema", "hg_runtime/fixture/schemas.py"),
        ("cc-duplicate-behavior", "duplicate_behavior_name", "hg_runtime/fixture/router.py"),
        ("cc-conflicting-owner", "conflicting_owner", "hg_runtime/fixture/owners.yaml"),
        ("cc-circular-dependency", "circular_dependency_candidate", "hg_runtime/fixture/a.py"),
        ("cc-test-leak", "test_only_logic_leak", "hg_runtime/fixture/runtime.py"),
        ("cc-mock-real", "mock_path_pretending_real", "hg_runtime/fixture/provider.py"),
        ("cc-silent-fallback", "silent_fallback_provider", "hg_runtime/fixture/provider_fallback.py"),
        ("cc-divergent-gate", "divergent_duplicate_gate", "scripts/evals/fixture_gate.py"),
        ("cc-many-owners", "one_behavior_many_owners", "hg_runtime/fixture/behavior.py"),
    ]


def build_code_cancer_finding(*, finding_id: str, finding_type: str, surface: str, severity: str = "WATCH") -> dict:
    finding = {
        "schema_version": "1",
        "record_type": "code_cancer_finding_v1",
        "finding_id": finding_id,
        "finding_type": finding_type,
        "surface": surface,
        "severity": severity,
        "repair_recommendation": "REQUEST_PATCH_CANDIDATE",
        "finding_is_not_authority": True,
        "detection_is_not_repair": True,
        "repair_recommendation_is_not_patch_permission": True,
        "automatic_patch_performed": False,
        "deletion_performed": False,
        "false_positive_requires_receipt": True,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def scan_code_cancer_fixtures() -> dict:
    findings = [
        build_code_cancer_finding(finding_id=finding_id, finding_type=finding_type, surface=surface)
        for finding_id, finding_type, surface in code_cancer_fixtures()
    ]
    manifest = {
        "schema_version": "1",
        "record_type": "code_cancer_manifest_v1",
        "manifest_id": "ais4-code-cancer-detector",
        "finding_count": len(findings),
        "finding_types": sorted({f["finding_type"] for f in findings}),
        "finding_hashes": [f["record_hash"] for f in findings],
        "finding_is_not_authority": True,
        "detection_is_not_repair": True,
        "repair_recommendation_is_not_patch_permission": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    replay = replay_code_cancer_scan(findings, manifest)
    return {"findings": findings, "manifest": manifest, "replay": replay}


def replay_code_cancer_scan(findings: list[dict], manifest: dict) -> dict:
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
        "record_type": "code_cancer_replay_record_v1",
        "replay_id": "ais4-code-cancer-replay",
        "replay_preserves_finding_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_code_cancer_finding(finding: dict) -> None:
    assert_neutral(finding)
    if finding.get("automatic_patch_performed") or finding.get("deletion_performed"):
        raise ValueError("code_cancer_finding_cannot_patch_or_delete")
    if not finding.get("finding_is_not_authority"):
        raise ValueError("finding_is_not_authority_required")
    if not finding.get("false_positive_requires_receipt"):
        raise ValueError("false_positive_receipt_required")
