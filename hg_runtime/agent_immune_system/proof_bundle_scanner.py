"""Scan proof bundles for required artifact presence."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.finding import build_finding

REQUIRED_FILES = (
    "gate_result.json",
    "report_snapshot.md",
    "redaction_audit.json",
)


def scan_proof_bundle(bundle_dir: Path) -> list[dict]:
    findings: list[dict] = []
    bundle_dir = Path(bundle_dir)
    label = bundle_dir.name

    for filename in REQUIRED_FILES:
        path = bundle_dir / filename
        if path.exists():
            continue
        finding_type = {
            "gate_result.json": "missing_gate_result",
            "report_snapshot.md": "missing_report_snapshot",
            "redaction_audit.json": "missing_redaction_audit",
        }[filename]
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-{finding_type}",
                finding_type=finding_type,
                severity="RED",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(path),
                blocks_green=True,
            )
        )

    manifest_candidates = list(bundle_dir.glob("*manifest*.json"))
    if not manifest_candidates and (bundle_dir / "gate_result.json").exists():
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-missing_manifest",
                finding_type="missing_proof_bundle_manifest",
                severity="YELLOW",
                safe_action="REQUEST_EVIDENCE",
                surface=str(bundle_dir),
                blocks_green=False,
            )
        )

    meta = bundle_dir / "scan_meta.json"
    if meta.exists():
        import json

        data = json.loads(meta.read_text(encoding="utf-8"))
        if data.get("untracked_generated_artifacts"):
            for artifact in data["untracked_generated_artifacts"]:
                findings.append(
                    build_finding(
                        record_type="record_health_finding_v1",
                        finding_id=f"rh-{label}-untracked-{artifact}",
                        finding_type="untracked_generated_artifact",
                        severity="YELLOW",
                        safe_action="REQUEST_OPERATOR_REVIEW",
                        surface=artifact,
                    )
                )

    return findings
