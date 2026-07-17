"""AIS-1 record health artifact writer and replay."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.health_signal import build_health_signal
from hg_runtime.agent_immune_system.record_health import scan_bundles, scan_bundle
from hg_runtime.agent_immune_system.redaction import secret_scan
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def findings_to_health_signals(findings: list[dict]) -> list[dict]:
    signals: list[dict] = []
    for finding in findings:
        signals.append(
            build_health_signal(
                signal_id=f"hs-{finding['finding_id']}",
                source_component="AISRecordAuditor",
                signal_type=finding["finding_type"],
                severity=finding["severity"],
                weight=1.0 if finding["severity"] in ("RED", "PANIC") else 0.5,
                evidence_ref=finding.get("surface", finding["finding_id"]),
                phase_ref=finding.get("extra", {}).get("phase_ref") if isinstance(finding.get("extra"), dict) else None,
            )
        )
    return signals


def replay_record_health(findings: list[dict], manifest: dict) -> dict:
    stored_hashes = [f["record_hash"] for f in findings]
    if stored_hashes != manifest.get("finding_hashes", []):
        return {"ok": False, "replay_preserves_scan_hashes": False, "failures": ["finding_hash_list_mismatch"]}
    for finding in findings:
        stored, recomputed = finding["record_hash"], record_hash({k: v for k, v in finding.items() if k != "record_hash"})
        if stored != recomputed:
            return {"ok": False, "replay_preserves_scan_hashes": False, "failures": [f"hash_mismatch:{finding['finding_id']}"]}
    return {"ok": True, "replay_preserves_scan_hashes": True, "failures": [], **neutral_flags()}


def build_record_health_layer(
    fixture_dirs: list[Path],
    reference_dirs: list[Path] | None = None,
) -> dict:
    fixture_findings = scan_bundles(fixture_dirs)
    reference_findings = scan_bundles(reference_dirs or [])

    findings = fixture_findings + reference_findings
    findings.sort(key=lambda f: f["finding_id"])

    for finding in findings:
        assert_neutral(finding)

    health_signals = findings_to_health_signals(findings)
    blocks_green = any(f.get("blocks_green") for f in findings)

    manifest = {
        "schema": "immune_scan_manifest_v1",
        "manifest_id": "ais1-record-health-scan",
        "fixture_bundle_count": len(fixture_dirs),
        "reference_bundle_count": len(reference_dirs or []),
        "finding_count": len(findings),
        "finding_hashes": [f["record_hash"] for f in findings],
        "blocks_green": blocks_green,
        "detection_is_not_authority": True,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)

    replay = replay_record_health(findings, manifest)

    finding_types = {f["finding_type"] for f in findings}

    summary = {
        "finding_count": len(findings),
        "health_signal_count": len(health_signals),
        "blocks_green": blocks_green,
        "finding_types": sorted(finding_types),
        "replay_preserves_scan_hashes": replay["replay_preserves_scan_hashes"],
    }
    summary["summary_hash"] = record_hash(summary)

    return {
        "findings": findings,
        "health_signals": health_signals,
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
        "fixture_findings": fixture_findings,
        "reference_findings": reference_findings,
    }
