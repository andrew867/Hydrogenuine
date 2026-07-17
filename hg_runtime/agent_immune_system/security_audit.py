"""AIS-6 defensive-only security audit scaffolding."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags

FINDING_TYPES = (
    "staged_secret_pattern",
    "hg_local_tracking_candidate",
    "unsafe_subprocess_candidate",
    "path_traversal_candidate",
    "unauthorized_network_call_path",
    "tool_authorization_bypass_candidate",
    "unsafe_deserialization_candidate",
    "prompt_injection_boundary_risk",
    "provider_trust_boundary_violation",
    "overly_broad_permission_candidate",
)


def security_audit_fixtures() -> list[tuple[str, str, str]]:
    return [
        ("sec-staged-secret", "staged_secret_pattern", "fixtures/security/staged_secret_label"),
        ("sec-hg-local", "hg_local_tracking_candidate", ".hg-local/fixture"),
        ("sec-subprocess", "unsafe_subprocess_candidate", "hg_runtime/fixture/subprocess_boundary.py"),
        ("sec-path", "path_traversal_candidate", "hg_runtime/fixture/path_boundary.py"),
        ("sec-network", "unauthorized_network_call_path", "hg_runtime/fixture/network_boundary.py"),
        ("sec-tool-bypass", "tool_authorization_bypass_candidate", "hg_runtime/fixture/tool_boundary.py"),
        ("sec-deserialization", "unsafe_deserialization_candidate", "hg_runtime/fixture/deserialization.py"),
        ("sec-prompt", "prompt_injection_boundary_risk", "hg_runtime/fixture/prompt_boundary.md"),
        ("sec-provider", "provider_trust_boundary_violation", "hg_runtime/fixture/provider_boundary.py"),
        ("sec-permission", "overly_broad_permission_candidate", "hg_runtime/fixture/permission_boundary.py"),
    ]


def build_security_finding(*, finding_id: str, finding_type: str, surface: str, severity: str = "WATCH") -> dict:
    finding = {
        "schema_version": "1",
        "record_type": "security_finding_v1",
        "finding_id": finding_id,
        "finding_type": finding_type,
        "surface": surface,
        "severity": severity,
        "audit_mode": "DEFENSIVE_ONLY_STATIC_LOCAL",
        "remediation_task": f"review:{finding_id}",
        "security_audit_is_defensive_only": True,
        "vulnerability_finding_is_not_attack_permission": True,
        "exploit_payload_included": False,
        "external_scan_performed": False,
        "live_network_used": False,
        "automatic_patch_performed": False,
        "findings_create_remediation_tasks_only": True,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_security_audit_layer() -> dict:
    findings = [
        build_security_finding(finding_id=finding_id, finding_type=finding_type, surface=surface)
        for finding_id, finding_type, surface in security_audit_fixtures()
    ]
    manifest = {
        "schema_version": "1",
        "record_type": "security_audit_manifest_v1",
        "manifest_id": "ais6-defensive-security-auditor",
        "audit_mode": "DEFENSIVE_ONLY_STATIC_LOCAL",
        "finding_count": len(findings),
        "finding_types": sorted({f["finding_type"] for f in findings}),
        "finding_hashes": [f["record_hash"] for f in findings],
        "security_audit_is_defensive_only": True,
        "vulnerability_finding_is_not_attack_permission": True,
        "no_exploit_payloads": True,
        "no_external_scanning": True,
        "no_live_network": True,
        "findings_create_remediation_tasks_only": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    replay = replay_security_audit_layer(findings, manifest)
    return {"findings": findings, "manifest": manifest, "replay": replay}


def replay_security_audit_layer(findings: list[dict], manifest: dict) -> dict:
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
        "record_type": "security_audit_replay_record_v1",
        "replay_id": "ais6-security-audit-replay",
        "replay_preserves_security_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_security_finding(finding: dict) -> None:
    assert_neutral(finding)
    if finding.get("exploit_payload_included"):
        raise ValueError("exploit_payload_forbidden")
    if finding.get("external_scan_performed") or finding.get("live_network_used"):
        raise ValueError("live_or_external_security_scan_forbidden")
    if finding.get("automatic_patch_performed"):
        raise ValueError("security_audit_cannot_patch")
